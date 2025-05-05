VERSION = "SP2_V0.0505a"

import machine
import binascii
from umqtt.simple import MQTTClient
import _thread
import utime
import network
import ujson
import gc
from machine import WDT
import os

# 定義狀態類型
class MainStatus:
    NONE_WIFI = 0       # 還沒連上WiFi
    NONE_INTERNET = 1   # 連上WiFi，但還沒連上外網      現在先不做這個判斷
    NONE_MQTT = 2       # 連上外網，但還沒連上MQTT Broker
    STANDBY_MQTT = 7    # 連上MQTT，正常運行中
    GOING_TO_OTA = 6    # 接收到要OTA，但還沒完成OTA
    UNEXPECTED_STATE = -1

# 定義狀態機類別
class MainStateMachine:
    def __init__(self):
        self.state = MainStatus.NONE_WIFI
        # 以下執行"狀態機初始化"相應的操作
        print('\n\rInit, MainStatus: NONE_WIFI')
        GPO_CardReader_EPAY_EN.value(0)   # Wi-Fi未連線、而且娃娃機連線未確定，暫停卡機支付功能
        global main_while_delay_seconds, LCD_update_flag
        main_while_delay_seconds = 1
        LCD_update_flag['Uniform'] = True

    def transition(self, action):
        global main_while_delay_seconds, LCD_update_flag
        if action == 'WiFi is disconnect':
            self.state = MainStatus.NONE_WIFI
            # 以下執行"未連上WiFi後"相應的操作
            print('\n\rAction: WiFi is disconnect, MainStatus: NONE_WIFI')
            GPO_CardReader_EPAY_EN.value(0)   # Wi-Fi未連線、而且娃娃機連線未確定，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True
        elif self.state == MainStatus.NONE_WIFI and action == 'WiFi is OK':
            self.state = MainStatus.NONE_INTERNET
            # 以下執行"連上WiFi後"相應的操作
            print('\n\rAction: WiFi is OK, MainStatus: NONE_INTERNET')
            GPO_CardReader_EPAY_EN.value(0)   # Wi-Fi已連線、但娃娃機連線未確定，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True
        elif self.state == MainStatus.NONE_INTERNET and action == 'Internet is OK':
            self.state = MainStatus.NONE_MQTT
            # 以下執行"連上Internet後"相應的操作
            print('\n\rAction: Internet is OK, MainStatus: NONE_MQTT')
            GPO_CardReader_EPAY_EN.value(0)   # 外網已連線、但娃娃機連線未確定，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True
        elif self.state == MainStatus.NONE_MQTT and action == 'MQTT is OK':
            self.state = MainStatus.STANDBY_MQTT
            # 以下執行"連上MQTT後"相應的操作
            print('\n\rAction: MQTT is OK, MainStatus: STANDBY_MQTT')
            GPO_CardReader_EPAY_EN.value(0)   # MQTT已連線，暫停卡機支付功能
            main_while_delay_seconds = 10
            LCD_update_flag['WiFi'] = True
            LCD_update_flag['Claw_State'] = True
            

        elif action == 'MQTT is not OK':
            self.state = MainStatus.NONE_MQTT
            # 以下執行"MQTT失敗後"相應的操作
            print('\n\rAction: MQTT is not OK, MainStatus: NONE_MQTT')
            GPO_CardReader_EPAY_EN.value(0)   # MQTT無法連線，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True
            
        else:
            print('\n\rInvalid action:', action, 'for current state:', self.state)
            main_while_delay_seconds = 1
 
# 開啟 token 檔案
def load_token():
    global token
    try:
        with open('token.dat') as f:
            token = f.readlines()[0].strip()
        print('Get token:', token)
        len_token = len(token)
        if len_token != 36:
            while True:
                print('token的長度不對:', len_token)
                utime.sleep(30)
    except Exception as e:
        print("Open token.dat failed:", e)
        while True:
            print('遺失 token 檔案')
            utime.sleep(30)

def get_wifi_signal_strength(wlan):
    if wlan.isconnected():
        signal_strength = wlan.status('rssi')
        return signal_strength
    else:
        return None

def connect_wifi():
    global wifi
    wifi = network.WLAN(network.STA_IF)

    if not wifi.config('essid'):
        print('沒有經過wifimgr.py')
        wifi_ssid = 'ThomasAP'
        wifi_password = '0988525509'
        wifi.active(True)
        wifi.connect(wifi_ssid, wifi_password)

    print('Start to connect WiFi, SSID : {}'.format(wifi.config('essid')))

    while True:
        for i in range(20):
            print('Try to connect WiFi in {}s'.format(i))
            utime.sleep(1)
            if wifi.isconnected():
                break
        if wifi.isconnected():
            print('WiFi connection OK!')
            print('Network Config=', wifi.ifconfig())
            connect_internet_data = InternetData()
            connect_internet_data.ip_address = wifi.ifconfig()[0]
            tmp_mac_address = wifi.config('mac')
            connect_internet_data.mac_address = ''.join(['{:02X}'.format(byte) for byte in tmp_mac_address])
            return connect_internet_data
        else:
            print('WiFi({}) connection Error'.format(wifi.config('essid')))
            for i in range(30, -1, -1):
                print("倒數{}秒後重新連線WiFi".format(i))
                utime.sleep(1)

class InternetData:
    def __init__(self):
        self.ip_address = ""
        self.mac_address = ""

def connect_mqtt():
    mq_server = 'happycollect.propskynet.com'
    mq_id = my_internet_data.mac_address
    mq_user = 'myuser'
    mq_pass = 'propskymqtt'
    while True:
        try:
            mq_client = MQTTClient(mq_id, mq_server, user=mq_user, password=mq_pass)
            mq_client.connect()
            print('MQTT Broker connection OK!')
            return mq_client
        except Exception as e:
            print("MQTT Broker connection failed:", e)
            for i in range(10, -1, -1):
                print("倒數{}秒後重新連線MQTT Broker".format(i))
                utime.sleep(1)

def subscribe_MQTT_claw_recive_callback(topic, message):
    print("MQTT Subscribe recive data")
    print("MQTT Subscribe topic:", topic)
    print("MQTT Subscribe data(JSON_str):", message)
    try:
        data = ujson.loads(message)
        print("MQTT Subscribe data:", data)
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token
        if topic.decode() == (mq_topic + '/fota'):
            otafile = 'otalist.dat'
            if ('file_list' in data) and ('password' in data):
                if data['password'] == 'c0b82a2c-4b03-42a5-92cd-3478798b2a90':
                    #print("password checked")
                    publish_MQTT_claw_data(analog_claw_1, 'fotaack')                    
                    with open(otafile, "w") as f:
                        f.write(''.join(data['file_list']))
                    print("otafile 輸出完成，即將重開機...")
                    utime.sleep(3)
                    machine.reset()
                else:
                    print("password failed")
        elif topic.decode() == (mq_topic + '/commands'):
            if data['commands'] == 'ping':
                publish_MQTT_claw_data(analog_claw_1, 'commandack-pong')
            elif data['commands'] == 'version':
                publish_MQTT_claw_data(analog_claw_1, 'commandack-version')
            elif data['commands'] == 'clawstartgame':
                if 'state' in data:
                    publish_MQTT_claw_data(analog_claw_1, 'commandack-clawstartgame',data['state'])
                    epays=data['epays'] 
                    freeplays=data['freeplays']
                    uart_FEILOLI_send_packet(KindFEILOLIcmd.Send_Starting_once_game)
            elif data['commands'] == 'fileinfo':
                publish_MQTT_claw_data(analog_claw_1, 'commandack-fileinfo',data['filename'])
                pass
            elif data['commands'] == 'fileremove':
                publish_MQTT_claw_data(analog_claw_1, 'commandack-fileremove',data['filename'])
                pass
            # elif data['commands'] == 'getstatus':
    except Exception as e:
        print("MQTT Subscribe data to JSON Error:", e)

def subscribe_MQTT_claw_topic():  # MQTT_client暫時固定為mq_client_1
    mq_client_1.set_callback(subscribe_MQTT_claw_recive_callback)
    macid = my_internet_data.mac_address
    mq_topic = macid + '/' + token + '/commands'
    mq_client_1.subscribe(mq_topic)
    print("MQTT Subscribe topic:", mq_topic)
    mq_topic = macid + '/' + token + '/fota'
    mq_client_1.subscribe(mq_topic)
    print("MQTT Subscribe topic:", mq_topic)

def publish_data(mq_client, topic, data):
    try:
        # mq_message = ujson.dumps(data)
        print("MQTT Publish topic:", topic)
        print("MQTT Publish data(JSON_str):", data)
        mq_client.publish(topic, data)
        print("MQTT Publish Successful")
    except Exception as e:
        print("MQTT Publish Error:", e)
        now_main_state.transition('MQTT is not OK')

def get_file_info(filename):
    try:
        file_stat = os.stat(filename)
        file_size = file_stat[6]  # Index 6 is the file size
        file_mtime = file_stat[8]  # Index 8 is the modification time
        return file_size, file_mtime
    except OSError:
        return None, None

def publish_MQTT_claw_data(claw_data, MQTT_API_select, para1=""):  # 可以選擇analog_claw_1、claw_2、...，但MQTT_client暫時固定為mq_client_1
    global wifi
    if MQTT_API_select == 'sales':
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/sales'
        MQTT_claw_data = {
            "Epayplaytimes": claw_data.Number_of_Original_Payment,
            "Coinplaytimes": claw_data.Number_of_Coin,
            "Giftplaytimes": claw_data.Number_of_Gift_Payment,
            "GiftOuttimes":  claw_data.Number_of_Award,
            "Freeplaytimes": claw_data.Number_of_Free_Payment,
            "time": utime.time()
        }
    elif MQTT_API_select == 'status':
        signal_strength = get_wifi_signal_strength(wifi)
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/status'
        if now_main_state.state == MainStatus.STANDBY_MQTT :
            MQTT_claw_data = {
                "status": "%02d" % (claw_data.Error_Code_of_Machine),
                "wifirssi": signal_strength,
                "time":   utime.time()
            }
        else :
            MQTT_claw_data = {
                "status": "%02d" % 99,
                "wifirssi": signal_strength,
                "time":   utime.time()
            }
    elif MQTT_API_select == 'commandack-pong':
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/commandack'
        MQTT_claw_data = {
            "ack": "pong",
            "time": utime.time()
        }
    elif MQTT_API_select == 'commandack-version':
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/commandack'
        MQTT_claw_data = {
            "ack":  VERSION,
            "time": utime.time()
        }
    elif MQTT_API_select == 'fotaack':
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/fotaack'
        MQTT_claw_data = {
            "ack": "OK",
            "time": utime.time()
        }          
    elif MQTT_API_select == 'commandack-clawstartgame':
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/commandack'
        if para1=="" :
            MQTT_claw_data = {
                "ack": "OK",
                "time": utime.time()
            }
        else :
            MQTT_claw_data = {
                "ack": "OK",
                "state" : para1,
                "time": utime.time()
            }
    elif MQTT_API_select == 'commandack-fileinfo':
        #check file exist, read file info
        file_name = para1
        file_exist = 0
        file_date = ""
        file_size = 0
        try:
            file_stat = os.stat(file_name)
            file_size, file_mtime = get_file_info(file_name)
            if file_size is not None:
                #print("File Size:", file_size, "bytes")

                if file_mtime is not None:
                    formatted_date = utime.localtime(file_mtime)
                    formatted_date_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                        formatted_date[0], formatted_date[1], formatted_date[2],
                        formatted_date[3], formatted_date[4], formatted_date[5]
                    )
                    file_date=formatted_date_str
                    file_exist=1
                    #print("File Date:", formatted_date_str)
                else:
                    file_exist=2
                    formatted_date_str="N/A"
                    #print("File Date: N/A")
            else:
                #print("Unable to retrieve file information.")
                file_exist=80
        except OSError:
            #print("File does not exist.")
            file_exist=0
        
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/commandack'
        MQTT_claw_data = {
            "ack": "OK",
            "exist" : file_exist,
            "date" : file_date,
            "size" : file_size,
            "time": utime.time()
        }             
    elif MQTT_API_select == 'commandack-fileremove':
        #check file exist
        #yes remove it, reply remove ok
        #no reply no file
        file_name = para1
        result=""
        try:
            file_stat = os.stat(file_name)
            if file_name != "main.py":
                os.remove(para1)
                result="remove ok"
            else:
                result="CAN NOT REMOVE main.py"

        except OSError:
            #print("File does not exist.")
            file_exist=0
            result="NO FILE!" 
        
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/commandack'
        MQTT_claw_data = {
            "ack": "OK",
            "result" : result,
            "time": utime.time()
        }              
    mq_json_str = ujson.dumps(MQTT_claw_data)
    publish_data(mq_client_1, mq_topic, mq_json_str)

class analogClawData:
    def __init__(self):
        self.Number_of_Original_Payment = 0     # for 三、帳目查詢\遠端帳目\悠遊卡支付次數
        self.Number_of_Gift_Payment = 0         # for 三、帳目查詢\遠端帳目\悠遊卡贈送次數
        self.Number_of_Free_Payment = 0         # for 三、帳目查詢\遠端帳目\悠遊卡贈送次數
        self.Number_of_Coin = 0                 # for 三、帳目查詢\遠端帳目\投幣次數
        self.Number_of_Award = 0                # for 三、帳目查詢\遠端帳目、投幣帳目\禮品出獎次數
        self.Error_Code_of_Machine = 99         # for 機台故障代碼表


claw_check_timer_period = 10        # 10, 單位秒
claw_check_timer_counter = 0
 
# 定義virtual timer 軟體計時器回調函式 (每1秒執行1次)
def three_timer_task():
    while True:
        try:
            global claw_check_timer_counter
            claw_check_timer_counter = (claw_check_timer_counter + 1) % claw_check_timer_period
            if claw_check_timer_counter == 0:
                claw_check_timer_callback()                
            if Rounds_of_Starting_games > 0:
                GPIO_Send_Starting_games()

            LCD_update_timer_callback()

            server_check_timer_callback()

        except OSError as e:
            print("3t error:", e)
        utime.sleep_ms(1000)                         # 休眠一小段時間，避免過度使用CPU資源

# 定義claw_check計時器回調函式
def claw_check_timer_callback():
    global counter_of_WAITING_FEILOLI
    # if now_main_state.state == MainStatus.NONE_FEILOLI:
    print("Updating 娃娃機 機台狀態 ...")

            
# 定義LCD_update計時器回調函式
def LCD_update_timer_callback():
    if LCD_update_flag['Uniform']:
        LCD_update_flag['Uniform'] = False
        unique_id_hex = binascii.hexlify(machine.unique_id()).decode().upper()
        dis.fill(color.BLACK)
        dis.draw_text(spleen16, 'Happy Collector', 0, 0, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0)
        dis.fgcolor = color.RED     # 设置前景颜色为紅色
        dis.bgcolor = color.WHITE   # 设置背景颜色为黑色
        dis.draw_text(spleen16, unique_id_hex, 5, 8 * 16 + 5, 1.3, dis.fgcolor, dis.bgcolor, -1, True, 0, 0) 
        dis.dev.show()
        dis.fgcolor = color.WHITE   # 设置前景颜色为白色
        dis.bgcolor = color.BLACK   # 设置背景颜色为黑色
        dis.draw_text(spleen16, 'IN:--------', 0, 1 * 16, 1, dis.fgcolor, dis.bgcolor, 0, True, 0, 0)
        dis.draw_text(spleen16, 'OUT:--------', 0, 2 * 16, 1, dis.fgcolor, dis.bgcolor, 0, True, 0, 0)
        dis.draw_text(spleen16, 'EP:--------', 0, 3 * 16, 1, dis.fgcolor, dis.bgcolor, 0, True, 0, 0)
        dis.draw_text(spleen16, 'FP:--------', 0, 4 * 16, 1, dis.fgcolor, dis.bgcolor, 0, True, 0, 0)
        dis.draw_text(spleen16, 'ST:--', 0, 5 * 16, 1, dis.fgcolor, dis.bgcolor, 0, True, 0, 0)
        dis.draw_text(spleen16, 'Time:mm/dd hh:mm', 0, 6 * 16, 1, dis.fgcolor, dis.bgcolor, 0, True, 0, 0)
        dis.draw_text(spleen16, 'Wifi:-----', 0, 7 * 16, 1, dis.fgcolor, dis.bgcolor, 0, True, 0, 0) 
        dis.dev.show()
    elif LCD_update_flag['WiFi']:
        LCD_update_flag['WiFi'] = False
        if now_main_state.state == MainStatus.NONE_WIFI or now_main_state.state == MainStatus.NONE_INTERNET:
            dis.draw_text(spleen16, 'dis  ', 5 * 8, 7 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0) #顯示wifi和MQTT狀態
        elif now_main_state.state == MainStatus.NONE_MQTT:
            dis.draw_text(spleen16, 'error', 5 * 8, 7 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0) #顯示wifi和MQTT狀態
        elif now_main_state.state == MainStatus.STANDBY_MQTT:
            dis.draw_text(spleen16, 'ok   ', 5 * 8, 7 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0) #顯示wifi和MQTT狀態
        dis.dev.show()
    elif LCD_update_flag['Claw_State']:
        LCD_update_flag['Claw_State'] = False  
        dis.draw_text(spleen16,  "%02d" % analog_claw_1.Error_Code_of_Machine, 3 * 8, 5 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0) #顯示娃娃機狀態
        dis.dev.show()
    elif LCD_update_flag['Claw_Value']:
        LCD_update_flag['Claw_Value'] = False
        # if now_main_state.state == MainStatus.STANDBY_FEILOLI or now_main_state.state == MainStatus.WAITING_FEILOLI:
        dis.draw_text(spleen16,  "%-8d" % analog_claw_1.Number_of_Coin, 3 * 8, 1 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0)
        dis.draw_text(spleen16,  "%-8d" % analog_claw_1.Number_of_Award, 4 * 8, 2 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0)
        dis.draw_text(spleen16,  "%-8d" % analog_claw_1.Number_of_Original_Payment, 3 * 8, 3 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0)
        dis.draw_text(spleen16,  "%-8d" % analog_claw_1.Number_of_Free_Payment, 3 * 8, 4 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0)
        dis.dev.show()
    elif (LCD_update_flag['Time']):
        LCD_update_flag['Time'] = False  
        # 获取当前时间戳
        timestamp = utime.time()
        # 转换为本地时间
        local_time = utime.localtime(timestamp)
        # 格式化为 "mm/dd hh:mm" 格式的字符串
        formatted_time = "{:02d}/{:02d} {:02d}:{:02d}".format(local_time[1], local_time[2], local_time[3], local_time[4])
        dis.draw_text(spleen16,  formatted_time, 5 * 8, 6 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0)    #顯示時間
        dis.dev.show()

# 定義server_check計時器回調函式 (每1秒執行1次)
def server_check_timer_callback():
    global WDT_feed_flag, mq_client_1
    if now_main_state.state == MainStatus.STANDBY_MQTT:
        try:
            # 更新 MQTT Subscribe
            mq_client_1.check_msg()
            #mq_client_1.ping()
        except OSError as e:
            print("WiFi is disconnect")
            now_main_state.transition('WiFi is disconnect')
            mq_client_1.disconnect()
            return

        global server_report_flag
        if server_report_flag == 1:
            server_report_flag = 0
            if now_main_state.state == MainStatus.STANDBY_MQTT :
                publish_MQTT_claw_data(analog_claw_1, 'sales')
            # if analog_claw_1.Error_Code_of_Machine != 0x00 :
            publish_MQTT_claw_data(analog_claw_1, 'status')
            WDT_feed_flag = 1

server_report_flag = 0
server_report_period = 3*6   # 3分鐘=3*6, 單位10秒
# server_report_period = 1   # For快速測試, 10秒=1, 單位10秒
server_report_counter = server_report_period - 3 # 開機後第一次送MQTT會縮短到30秒
# 定義server_report計時器回調函式 (每1秒執行1次)
def server_report_timer_callback(timer):
    global server_report_counter, server_report_flag
    server_report_counter = (server_report_counter + 1) % server_report_period
    if server_report_counter == 0:
        server_report_flag = 1


# 定義GPI中斷處理函式
PAYOUT_falling_time = utime.ticks_ms()
PAYOUT_last_rising_time = utime.ticks_ms()
Coin_IN1_falling_time = utime.ticks_ms()
Coin_IN1_last_rising_time = utime.ticks_ms()
Coin_IN2_falling_time = utime.ticks_ms()
Coin_IN2_last_rising_time = utime.ticks_ms()
def GPI_interrupt_handler(pin):
    
    if pin == GPIO_CardReader_PAYOUT :
        global PAYOUT_falling_time, PAYOUT_last_rising_time
        PAYOUT_value = GPIO_CardReader_PAYOUT.value()
        PAYOUT_now_time = utime.ticks_ms()
        print("PAYOUT收到中斷:", PAYOUT_value)
        if PAYOUT_value == 0 :
            PAYOUT_falling_time = PAYOUT_now_time
        elif PAYOUT_value == 1 :
            PAYOUT_rising_time = PAYOUT_now_time
            PAYOUT_hipulse_time = PAYOUT_falling_time - PAYOUT_last_rising_time
            PAYOUT_lowpulse_time = PAYOUT_rising_time - PAYOUT_falling_time
            print("中斷PAYOUT收到Hi Pulse，寬度(ms):", PAYOUT_hipulse_time, ",和Low Pulse，寬度(ms):", PAYOUT_lowpulse_time)
            if PAYOUT_hipulse_time >= 100 and (50 <= PAYOUT_lowpulse_time and PAYOUT_lowpulse_time <=200) :
                # print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲。硬體已直通，暫不走韌體啟動")
                print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲。")
                global Rounds_of_Starting_games
                Rounds_of_Starting_games = Rounds_of_Starting_games + 1 
            else :
                print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
            PAYOUT_last_rising_time = PAYOUT_rising_time
    
    if pin == GPI_Claw_Coin_IN1 :
        global Coin_IN1_falling_time, Coin_IN1_last_rising_time
        Coin_IN1_value = GPI_Claw_Coin_IN1.value()
        Coin_IN1_now_time = utime.ticks_ms()
        print("Coin_IN1收到中斷:", Coin_IN1_value)
        if Coin_IN1_value == 0 :
            Coin_IN1_falling_time = Coin_IN1_now_time
        elif Coin_IN1_value == 1 :
            Coin_IN1_rising_time = Coin_IN1_now_time
            Coin_IN1_hipulse_time = Coin_IN1_falling_time - Coin_IN1_last_rising_time
            Coin_IN1_lowpulse_time = Coin_IN1_rising_time - Coin_IN1_falling_time
            print("中斷Coin_IN1收到Hi Pulse，寬度(ms):", Coin_IN1_hipulse_time, ",和Low Pulse，寬度(ms):", Coin_IN1_lowpulse_time)
            if Coin_IN1_hipulse_time >= 100 and (10 <= Coin_IN1_lowpulse_time and Coin_IN1_lowpulse_time <=200) :
                print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲")
                global Rounds_of_Starting_games
                Rounds_of_Starting_games = Rounds_of_Starting_games + 1 
            else :
                print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
            Coin_IN1_last_rising_time = Coin_IN1_rising_time
        
            
#    print('PAYOUT_end_time(ms):', time.ticks_ms())


# 定義啟動娃娃機遊戲的函式
Rounds_of_Starting_games = 0
def GPIO_Send_Starting_games():
    global Rounds_of_Starting_games
    print('GPIO_Send_Starting_games (次):', Rounds_of_Starting_games)
    while Rounds_of_Starting_games > 0:
        GPO_Claw_CoinPayOUT.value(1)
#        utime.sleep_ms(500)
        GPO_Claw_CoinPayOUT.value(0)
        utime.sleep_ms(50)
        GPO_Claw_CoinPayOUT.value(1)
        Rounds_of_Starting_games = Rounds_of_Starting_games -1
        # 這邊要寫JSON值
        if Rounds_of_Starting_games > 0:
            utime.sleep_ms(100)



############################################# 初始化 #############################################

print('\n\r開始執行 analogCoinPay_Main.py初始化，版本為:', VERSION)
print('開機秒數:', utime.ticks_ms() / 1000)

# import micropython
gc.collect()
# print(micropython.mem_info())
print(gc.mem_free())
          
# 開啟 token 檔案
load_token()

WDT_feed_flag = 0
wdt=WDT(timeout=1000*60*10)

print('1開機秒數:', utime.ticks_ms() / 1000)
# LCD配置
try:
    print(st7735)
except Exception as e:
    print('沒有經過main.py:', e)
    try:
        from dr.st7735.st7735_4bit import ST7735
        from machine import SPI, Pin
        LCD_EN = machine.Pin(27, machine.Pin.OUT)
        LCD_EN.value(1)
        spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(14), mosi=Pin(13))
        st7735 = ST7735(spi, 4, 15, None, 128, 160, rotate=0)
        st7735.initb2()
        st7735.setrgb(True)
        from gui.colors import colors
        color = colors(st7735)
        from dr.display import display
        import fonts.spleen16 as spleen16
        dis = display(st7735, 'ST7735_FB', color.WHITE, color.BLUE)
        print(st7735)
    except Exception as e:
        print('st7735 init Error:', e)
        machine.reset()
LCD_update_flag = {
    'Uniform': True,
    'WiFi': False,
    'Time': False,
    'Claw_State': False,
    'Claw_Value': False,
}

print('2開機秒數:', utime.ticks_ms() / 1000)

# GPIO配置
# 卡機端的TV-1QR、觸控按鈕配置
GPIO_CardReader_PAYOUT = machine.Pin(25, machine.Pin.IN)
# GPIO_CardReader_PAYOUT = machine.Pin(36, machine.Pin.IN)
GPO_CardReader_EPAY_EN = machine.Pin(2, machine.Pin.OUT)
GPO_CardReader_EPAY_EN.value(1) # 先直接開通
GPO_CardReader_PAYINOUT_EN = machine.Pin(19, machine.Pin.OUT)
GPO_CardReader_PAYINOUT_EN.value(1) # 先直接開通s

# 娃娃機端的投幣器、電眼配置
GPI_Claw_Coin_IN1 = machine.Pin(16, machine.Pin.IN)
GPI_Claw_Coin_IN2 = machine.Pin(39, machine.Pin.IN)
GPO_Claw_Coin_EN = machine.Pin(5, machine.Pin.OUT)
GPO_Claw_Coin_EN.value(1) # 未來後台決定是否開通投幣器功能
GPO_Claw_CoinPayOUT = machine.Pin(26, machine.Pin.OPEN_DRAIN)
GPO_Claw_CoinPayOUT.value(1)

# GPIO 中斷配置
# 設定TV-1QR PAYOUT中斷，觸發條件為正緣和負緣
GPIO_CardReader_PAYOUT.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
GPI_Claw_Coin_IN1.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
#GPI_Claw_Coin_IN2.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)

# 創建狀態機
now_main_state = MainStateMachine()
# 創建娃娃機資料
analog_claw_1 = analogClawData()
# 創建 MQTT Client 1 資料
mq_client_1 = None
# 建立並執行 three_timer_task
_thread.start_new_thread(three_timer_task, ())
# 創建計時器物件
server_report_timer = machine.Timer(0)
# 設定server_report計時器的間隔和回調函式
TIMER_INTERVAL = 10000  # 設定10秒鐘 = 10000（單位：毫秒）
server_report_timer.init(period=TIMER_INTERVAL, mode=machine.Timer.PERIODIC, callback=server_report_timer_callback)

last_time = 0
main_while_delay_seconds = 1
while True:

    utime.sleep_ms(500)
    if WDT_feed_flag == 1 :
        WDT_feed_flag = 0
        wdt.feed()
        print('WDT fed! 開機秒數:', utime.ticks_ms() / 1000)

    current_time = utime.ticks_ms()
    if (utime.ticks_diff(current_time, last_time) >= main_while_delay_seconds * 1000):
        last_time = utime.ticks_ms()

        if now_main_state.state == MainStatus.NONE_WIFI:
            print('\n\rnow_main_state: WiFi is disconnect, 開機秒數:', current_time / 1000)
            my_internet_data = connect_wifi()
            # 打印 myInternet 内容
            print("My IP Address:", my_internet_data.ip_address)
            print("My MAC Address:", my_internet_data.mac_address)
            now_main_state.transition('WiFi is OK')
        elif now_main_state.state == MainStatus.NONE_INTERNET:
            print('\n\rnow_main_state: WiFi is OK, 開機秒數:', current_time / 1000)
            now_main_state.transition('Internet is OK')  # 目前不做判斷，狀態機直接往下階段跳轉
        elif now_main_state.state == MainStatus.NONE_MQTT:
            print('now_main_state: Internet is OK, 開機秒數:', current_time / 1000)
            mq_client_1 = connect_mqtt()
            if mq_client_1 is not None:
                try:
                    subscribe_MQTT_claw_topic()
                    now_main_state.transition('MQTT is OK')
                except:
                    print('MQTT subscription has failed')
            gc.collect()
            print(gc.mem_free())
        elif now_main_state.state == MainStatus.STANDBY_MQTT:
            print('\n\rnow_main_state: MQTT is OK, 開機秒數:', current_time / 1000)
            gc.collect()
            print(gc.mem_free())
        else:
            print('\n\rInvalid action! now_main_state:', now_main_state.state)
            print('開機秒數:', current_time / 1000)

        LCD_update_flag['Time'] = True
