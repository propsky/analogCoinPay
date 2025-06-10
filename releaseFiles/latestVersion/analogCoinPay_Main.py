VERSION = "SP2_V0.0610sa"

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
from mach_meter import MachMeter

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
        global main_while_delay_seconds, LCD_update_flag
        main_while_delay_seconds = 1
        LCD_update_flag['Uniform'] = True

    def transition(self, action):
        global main_while_delay_seconds, LCD_update_flag
        if action == 'WiFi is disconnect':
            self.state = MainStatus.NONE_WIFI
            # 以下執行"未連上WiFi後"相應的操作
            print('\n\rAction: WiFi is disconnect, MainStatus: NONE_WIFI')
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True
        elif self.state == MainStatus.NONE_WIFI and action == 'WiFi is OK':
            self.state = MainStatus.NONE_INTERNET
            # 以下執行"連上WiFi後"相應的操作
            print('\n\rAction: WiFi is OK, MainStatus: NONE_INTERNET')
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True
        elif self.state == MainStatus.NONE_INTERNET and action == 'Internet is OK':
            self.state = MainStatus.NONE_MQTT
            # 以下執行"連上Internet後"相應的操作
            print('\n\rAction: Internet is OK, MainStatus: NONE_MQTT')
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True
        elif self.state == MainStatus.NONE_MQTT and action == 'MQTT is OK':
            self.state = MainStatus.STANDBY_MQTT
            # 以下執行"連上MQTT後"相應的操作
            print('\n\rAction: MQTT is OK, MainStatus: STANDBY_MQTT')
            main_while_delay_seconds = 10
            LCD_update_flag['WiFi'] = True

            ''' # 這作法不順利，先不用
            elif action == 'MQTT is disconnect':
                self.state = MainStatus.NONE_MQTT
                # 以下執行"MQTT失敗後"相應的操作
                print('\n\rAction: MQTT is disconnect, MainStatus: NONE_MQTT')
                mq_client_1.disconnect()
                now_main_state.transition('WiFi is disconnect')
                main_while_delay_seconds = 1
                LCD_update_flag['WiFi'] = True
            '''

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
    global WDT_feed_flag, wifi
    wifi = network.WLAN(network.STA_IF)
    if not wifi.config('essid'):
        print('沒有經過wifimgr.py')
        wifi_ssid = 'ThomasAP'
        wifi_password = '0988525509'
        wifi.active(True)
        wifi.connect(wifi_ssid, wifi_password)

    WDT_feed_flag = 1

    print('Start to connect WiFi, SSID : {}'.format(wifi.config('essid')))
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
        for i in range(20, -1, -1):
            print("倒數{}秒後重新連線WiFi".format(i))
            utime.sleep(1)
        return None

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
                    global Rounds_of_Starting_games
                    Rounds_of_Starting_games = Rounds_of_Starting_games + epays + freeplays
                    while epays > 0:
                        analog_claw_1.Number_of_Original_Payment = meter.inc_epay()
                        epays = epays - 1
                    while freeplays > 0:
                        analog_claw_1.Number_of_Free_Payment     = meter.inc_fplay()
                        freeplays = freeplays - 1
                    meter.save()
                    LCD_update_flag['Claw_Value'] = True
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
        mq_client_1.disconnect()
        now_main_state.transition('WiFi is disconnect')

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
    macid = my_internet_data.mac_address
    mq_topic = macid + '/' + token
    if MQTT_API_select == 'sales':
        mq_topic = mq_topic + '/sales'
        MQTT_claw_data = {
            "Epayplaytimes": claw_data.Number_of_Original_Payment,
            "Coinplaytimes": claw_data.Number_of_Coin,
            "Giftplaytimes": claw_data.Number_of_Gift_Payment,
            "GiftOuttimes":  claw_data.Number_of_Award,
            "Freeplaytimes": claw_data.Number_of_Free_Payment,
            "time": utime.time()
        }
    elif MQTT_API_select == 'status':
        mq_topic = mq_topic + '/status'
        signal_strength = get_wifi_signal_strength(wifi)
        MQTT_claw_data = {
            "status": "%02d" % (claw_data.Error_Code_of_Machine%100),
            "wifirssi": signal_strength,
            "time":   utime.time()
        }
    elif MQTT_API_select == 'commandack-pong':
        mq_topic = mq_topic + '/commandack'
        MQTT_claw_data = {
            "ack": "pong",
            "time": utime.time()
        }
    elif MQTT_API_select == 'commandack-version':
        mq_topic = mq_topic + '/commandack'
        MQTT_claw_data = {
            "ack":  VERSION,
            "time": utime.time()
        }
    elif MQTT_API_select == 'fotaack':
        mq_topic = mq_topic + '/fotaack'
        MQTT_claw_data = {
            "ack": "OK",
            "time": utime.time()
        }          
    elif MQTT_API_select == 'commandack-clawstartgame':
        mq_topic = mq_topic + '/commandack'
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
        mq_topic = mq_topic + '/commandack'
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
        MQTT_claw_data = {
            "ack": "OK",
            "exist" : file_exist,
            "date" : file_date,
            "size" : file_size,
            "time": utime.time()
        }             
    elif MQTT_API_select == 'commandack-fileremove':
        mq_topic = mq_topic + '/commandack'
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
        MQTT_claw_data = {
            "ack": "OK",
            "result" : result,
            "time": utime.time()
        }              
    mq_json_str = ujson.dumps(MQTT_claw_data)
    publish_data(mq_client_1, mq_topic, mq_json_str)

class analogClawData:
    def __init__(self):
        self.Number_of_Original_Payment = 0     # for 悠遊卡支付次數
        self.Number_of_Gift_Payment = 0         # for 悠遊卡贈送次數
        self.Number_of_Free_Payment = 0         # for Sam 補幣次數
        self.Number_of_Coin = 0                 # for 投幣次數
        self.Number_of_Award = 0                # for 禮品出獎次數
        self.Error_Code_of_Machine = 99         # for 機台故障代碼表
 
# 定義virtual timer 軟體計時器回調函式 (每1秒執行1次)
def three_timer_task():
    while True:
        try:
            claw_check_timer_callback()
            if Rounds_of_Starting_games > 0:
                GPIO_Send_Starting_games()
            LCD_update_timer_callback()
            server_check_timer_callback()

        except OSError as e:
            print("3t error:", e)
        utime.sleep_ms(500)                         # 休眠一小段時間，避免過度使用CPU資源

# 定義claw_check計時器回調函式
def claw_check_timer_callback():
    # print("Updating 娃娃機 機台狀態 ...")
    global Fault_Detect_last_value
    Fault_Detect_value = GPI_Claw_Fault_Detect.value()
    if Fault_Detect_value != Fault_Detect_last_value:
        print("Fault_Detect改變成:", Fault_Detect_value)
        GPIO_Setting_Coin_and_CardReader(Fault_Detect_value)
    Fault_Detect_last_value = Fault_Detect_value

# 定義LCD_update計時器回調函式
def LCD_update_timer_callback():
    if LCD_update_flag['Uniform']:
        LCD_update_flag['Uniform'] = False
        unique_id_hex = binascii.hexlify(machine.unique_id()).decode().upper()
        lcd_mgr.fill()  # 使用預設顏色（黑色）
        lcd_mgr.draw_text(0, 0, fg=lcd_mgr.color.WHITE, bg=lcd_mgr.color.BLUE, bgmode=-1)
        lcd_mgr.draw_text(5, 8 * 16 + 5, text=unique_id_hex, fg=lcd_mgr.color.RED, bg=lcd_mgr.color.WHITE, bgmode=-1, scale=1.3) 
        lcd_mgr.show()
        lcd_mgr.draw_text(0, 1 * 16, text='IN:--------') 
        lcd_mgr.draw_text(0, 2 * 16, text='OUT:--------') 
        lcd_mgr.draw_text(0, 3 * 16, text='EP:--------') 
        lcd_mgr.draw_text(0, 4 * 16, text='FP:--------') 
        lcd_mgr.draw_text(0, 5 * 16, text='ST:--') 
        lcd_mgr.draw_text(0, 6 * 16, text='Time:mm/dd hh:mm') 
        lcd_mgr.draw_text(0, 7 * 16, text='Wifi:-----')
        lcd_mgr.show()
    elif LCD_update_flag['WiFi']: # 顯示wifi和MQTT狀態
        LCD_update_flag['WiFi'] = False
        if now_main_state.state == MainStatus.NONE_WIFI or now_main_state.state == MainStatus.NONE_INTERNET:
            lcd_mgr.draw_text(5 * 8, 7 * 16, text='dis  ', bgmode=-1)
            # dis.draw_text(spleen16, 'dis  ', 5 * 8, 7 * 16, 1, dis.fgcolor, dis.bgcolor, -1, True, 0, 0) #顯示wifi和MQTT狀態
        elif now_main_state.state == MainStatus.NONE_MQTT:
            lcd_mgr.draw_text(5 * 8, 7 * 16, text='error', bgmode=-1)
        elif now_main_state.state == MainStatus.STANDBY_MQTT:
            lcd_mgr.draw_text(5 * 8, 7 * 16, text='ok   ', bgmode=-1)
        lcd_mgr.show()
    elif LCD_update_flag['Claw_State']: # 顯示娃娃機狀態
        LCD_update_flag['Claw_State'] = False  
        lcd_mgr.draw_text(3 * 8, 5 * 16, text=("%02d" % (analog_claw_1.Error_Code_of_Machine%100)), bgmode=-1)
        lcd_mgr.show()
    elif LCD_update_flag['Claw_Value']: # 顯示娃娃機數值
        LCD_update_flag['Claw_Value'] = False
        lcd_mgr.draw_text(3 * 8, 1 * 16, text=("%-8d" % analog_claw_1.Number_of_Coin), bgmode=-1)
        lcd_mgr.draw_text(4 * 8, 2 * 16, text=("%-8d" % analog_claw_1.Number_of_Award), bgmode=-1)
        lcd_mgr.draw_text(3 * 8, 3 * 16, text=("%-8d" % analog_claw_1.Number_of_Original_Payment), bgmode=-1)
        lcd_mgr.draw_text(3 * 8, 4 * 16, text=("%-8d" % analog_claw_1.Number_of_Free_Payment), bgmode=-1)
        lcd_mgr.show()
    elif (LCD_update_flag['Time']): # 顯示時間
        LCD_update_flag['Time'] = False  
        # 获取当前时间戳
        timestamp = utime.time()
        # 转换为本地时间
        local_time = utime.localtime(timestamp)
        # 格式化为 "mm/dd hh:mm" 格式的字符串
        formatted_time = "{:02d}/{:02d} {:02d}:{:02d}".format(local_time[1], local_time[2], local_time[3], local_time[4])
        lcd_mgr.draw_text(5 * 8, 6 * 16, text=formatted_time, bgmode=-1)
        lcd_mgr.show()

# 定義server_check計時器回調函式 (每1秒執行1次)
def server_check_timer_callback():
    global WDT_feed_flag, mq_client_1, server_report_flag
    if now_main_state.state == MainStatus.STANDBY_MQTT:
        try:
            # 更新 MQTT Subscribe
            mq_client_1.check_msg()
            #mq_client_1.ping()

            if server_report_flag == 1:
                server_report_flag = 0
                if now_main_state.state == MainStatus.STANDBY_MQTT :
                    publish_MQTT_claw_data(analog_claw_1, 'sales')
                    publish_MQTT_claw_data(analog_claw_1, 'status')
                    WDT_feed_flag = 1
    
        except OSError as e:
            print("MQTT Check Error:", e)
            # mq_client_1.disconnect()
            now_main_state.transition('WiFi is disconnect')
            return

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
PAYOUT_last_falling_time = utime.ticks_ms()
PAYOUT_last_rising_time = utime.ticks_ms()
Coin_IN1_last_falling_time = utime.ticks_ms()
Coin_IN1_last_rising_time = utime.ticks_ms()
Coin_IN2_last_falling_time = utime.ticks_ms()
Coin_IN2_last_rising_time = utime.ticks_ms()
Eyes_IROUT_last_falling_time = utime.ticks_ms()
Eyes_IROUT_last_rising_time = utime.ticks_ms()
Is_FEILOLI_eyes = 0
def GPI_interrupt_handler(pin):
    
    if pin == GPIO_CardReader_PAYOUT :
        global PAYOUT_last_falling_time, PAYOUT_last_rising_time
        PAYOUT_value = GPIO_CardReader_PAYOUT.value()
        PAYOUT_now_time = utime.ticks_ms()
        print("PAYOUT收到中斷:", PAYOUT_value)
        if PAYOUT_value == 0 :      # 1->0
            PAYOUT_last_falling_time = PAYOUT_now_time
        elif PAYOUT_value == 1 :    # 0->1
            PAYOUT_rising_time = PAYOUT_now_time
            PAYOUT_hipulse_time = PAYOUT_last_falling_time - PAYOUT_last_rising_time
            PAYOUT_lowpulse_time = PAYOUT_rising_time - PAYOUT_last_falling_time
            print("中斷PAYOUT收到Hi Pulse寬度(ms):", PAYOUT_hipulse_time, ",和Low Pulse寬度(ms):", PAYOUT_lowpulse_time)
            if PAYOUT_hipulse_time >= 100 and (50 <= PAYOUT_lowpulse_time and PAYOUT_lowpulse_time <=200) :
                # print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲。硬體已直通，暫不走韌體啟動")
                print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲。")
                global Rounds_of_Starting_games
                Rounds_of_Starting_games = Rounds_of_Starting_games + 1
                analog_claw_1.Number_of_Original_Payment = meter.inc_epay()
                meter.save()
                LCD_update_flag['Claw_Value'] = True
            else :
                print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
            PAYOUT_last_rising_time = PAYOUT_rising_time
    
    if pin == GPI_Claw_Coin_IN1 :
        global Coin_IN1_last_falling_time, Coin_IN1_last_rising_time
        Coin_IN1_value = GPI_Claw_Coin_IN1.value()
        Coin_IN1_now_time = utime.ticks_ms()
        print("Coin_IN1收到中斷:", Coin_IN1_value)
        if Coin_IN1_value == 0 :      # 1->0
            Coin_IN1_last_falling_time = Coin_IN1_now_time
        elif Coin_IN1_value == 1 :    # 0->1
            Coin_IN1_rising_time = Coin_IN1_now_time
            Coin_IN1_hipulse_time = Coin_IN1_last_falling_time - Coin_IN1_last_rising_time
            Coin_IN1_lowpulse_time = Coin_IN1_rising_time - Coin_IN1_last_falling_time
            print("中斷Coin_IN1收到Hi Pulse寬度(ms):", Coin_IN1_hipulse_time, ",和Low Pulse寬度(ms):", Coin_IN1_lowpulse_time)
            if Coin_IN1_hipulse_time >= 100 and (10 <= Coin_IN1_lowpulse_time and Coin_IN1_lowpulse_time <=200) :
                print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲")
                global Rounds_of_Starting_games
                Rounds_of_Starting_games = Rounds_of_Starting_games + 1
                analog_claw_1.Number_of_Coin  = meter.inc_in()
                meter.save()
                LCD_update_flag['Claw_Value'] = True
            else :
                print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
            Coin_IN1_last_rising_time = Coin_IN1_rising_time
    
    if pin == GPI_Claw_Coin_IN2 :
        global Coin_IN2_last_falling_time, Coin_IN2_last_rising_time
        Coin_IN2_value = GPI_Claw_Coin_IN2.value()
        Coin_IN2_now_time = utime.ticks_ms()
        print("Coin_IN2收到中斷:", Coin_IN2_value)
        if Coin_IN2_value == 0 :      # 1->0
            Coin_IN2_last_falling_time = Coin_IN2_now_time
        elif Coin_IN2_value == 1 :    # 0->1
            Coin_IN2_rising_time = Coin_IN2_now_time
            Coin_IN2_hipulse_time = Coin_IN2_last_falling_time - Coin_IN2_last_rising_time
            Coin_IN2_lowpulse_time = Coin_IN2_rising_time - Coin_IN2_last_falling_time
            print("中斷Coin_IN2收到Hi Pulse寬度(ms):", Coin_IN2_hipulse_time, ",和Low Pulse寬度(ms):", Coin_IN2_lowpulse_time)
            if Coin_IN2_hipulse_time >= 100 and (10 <= Coin_IN2_lowpulse_time and Coin_IN2_lowpulse_time <=200) :
                print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲")
                global Rounds_of_Starting_games
                Rounds_of_Starting_games = Rounds_of_Starting_games + 1
                analog_claw_1.Number_of_Coin  = meter.inc_in()
                meter.save()
                LCD_update_flag['Claw_Value'] = True
            else :
                print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
            Coin_IN2_last_rising_time = Coin_IN2_rising_time
    
    if pin == GPI_Claw_Eyes_IROUT :
        global Eyes_IROUT_last_falling_time, Eyes_IROUT_last_rising_time, Is_FEILOLI_eyes
        Eyes_IROUT_value = GPI_Claw_Eyes_IROUT.value()
        Eyes_IROUT_now_time = utime.ticks_ms()
        Eyes_IRDIS_value = GPI_Claw_Eyes_IRDIS.value()
        if  Eyes_IRDIS_value == 1 :
            Is_FEILOLI_eyes = 1
        print("Eyes_IROUT收到中斷:", Eyes_IROUT_value)
        print("Eyes_IRDIS:", Eyes_IRDIS_value)
        if Eyes_IROUT_value == 0 :      # 1->0
            Eyes_IROUT_falling_time = Eyes_IROUT_now_time
            if  Is_FEILOLI_eyes == 0 :
                Eyes_IROUT_lowpulse_time = Eyes_IROUT_last_rising_time - Eyes_IROUT_last_falling_time
                Eyes_IROUT_hipulse_time = Eyes_IROUT_falling_time - Eyes_IROUT_last_rising_time
                print("中斷Eyes_IROUT收到Low Pulse寬度(ms):", Eyes_IROUT_lowpulse_time, ",和Hi Pulse寬度(ms):", Eyes_IROUT_hipulse_time)
                if Eyes_IROUT_lowpulse_time >= 500 and (10 <= Eyes_IROUT_hipulse_time and Eyes_IROUT_hipulse_time <=800) :
                    print("通用電眼Pulse的Lo和Hi寬度都正確，出獎+1")
                    analog_claw_1.Number_of_Award = meter.inc_out()
                    meter.save()
                    LCD_update_flag['Claw_Value'] = True
                else :
                    print("通用電眼Pulse的Lo或Hi寬度不正確，不進行任何動作")
            Eyes_IROUT_last_falling_time = Eyes_IROUT_falling_time
        elif Eyes_IROUT_value == 1 :    # 0->1
            Eyes_IROUT_rising_time = Eyes_IROUT_now_time
            if  Is_FEILOLI_eyes == 1 :
                Eyes_IROUT_hipulse_time = Eyes_IROUT_last_falling_time - Eyes_IROUT_last_rising_time
                Eyes_IROUT_lowpulse_time = Eyes_IROUT_rising_time - Eyes_IROUT_last_falling_time
                print("中斷Eyes_IROUT收到Hi Pulse寬度(ms):", Eyes_IROUT_hipulse_time, ",和Low Pulse寬度(ms):", Eyes_IROUT_lowpulse_time)
                if Eyes_IROUT_hipulse_time >= 500 and (10 <= Eyes_IROUT_lowpulse_time and Eyes_IROUT_lowpulse_time <=800) : # 測試出飛絡力800ms以內算出獎
                    print("飛絡力電眼Pulse的Hi和Lo寬度都正確，出獎+1")
                    analog_claw_1.Number_of_Award = meter.inc_out()
                    meter.save()
                    LCD_update_flag['Claw_Value'] = True
                else :
                    print("飛絡力電眼Pulse的Hi或Lo寬度不正確，不進行任何動作")
            Eyes_IROUT_last_rising_time = Eyes_IROUT_rising_time

    '''
    if pin == GPI_Claw_Fault_Detect :
        Fault_Detect_value = GPI_Claw_Fault_Detect.value()
        print("Fault_Detect收到中斷:", Fault_Detect_value)
        GPIO_Setting_Coin_and_CardReader(Fault_Detect_value)
    '''

       

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
        if Rounds_of_Starting_games > 0:
            utime.sleep_ms(100)

# 定義偵測娃娃機故障處理的函式
def GPIO_Setting_Coin_and_CardReader(Is_Fault):
    if Is_Fault == 1: # 娃娃機故障
        GPO_CardReader_EPAY_EN.value(0)
        GPO_Claw_Coin_EN.value(0)
        if (analog_claw_1.Error_Code_of_Machine%100) != 24:
            analog_claw_1.Error_Code_of_Machine = analog_claw_1.Error_Code_of_Machine*100 + 24
    else:
        GPO_CardReader_EPAY_EN.value(1)
        GPO_Claw_Coin_EN.value(1)
        if (analog_claw_1.Error_Code_of_Machine%100) == 24:
            analog_claw_1.Error_Code_of_Machine = (analog_claw_1.Error_Code_of_Machine-24)/100
    LCD_update_flag['Claw_State'] = True


############################################# 初始化 #############################################

print('\n\r開始執行 analogCoinPay_Main.py初始化，版本為:', VERSION)
print('開機秒數:', utime.ticks_ms() / 1000)

gc.collect()
# print(micropython.mem_info())
print(gc.mem_free())
          
# 開啟 token 檔案
load_token()

WDT_feed_flag = 0
wdt=WDT(timeout=1000*60*10) # 10分鐘
print('1開機秒數:', utime.ticks_ms() / 1000)

# LCD配置
try:
    # 把st7735所有相關的模組都寫在lcd_manager
    # 獲取 LCD 單例singleton
    lcd_mgr = LCDManager.get_instance() 
    # LCD單例初始化
    lcd_mgr.initialize()
    gc.collect()
    print(gc.mem_free())
except Exception as e:
    print('LCD init Error:', e)
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
# 卡機端的TV-1、觸控按鈕配置
GPIO_CardReader_PAYOUT = machine.Pin(25, machine.Pin.IN)
GPO_CardReader_EPAY_EN = machine.Pin(2, machine.Pin.OUT)
GPO_CardReader_EPAY_EN.value(0)
GPO_CardReader_PAYINOUT_EN = machine.Pin(19, machine.Pin.OUT)
GPO_CardReader_PAYINOUT_EN.value(1) # 先直接開通
GPO_CardReader_I2C_EN = machine.Pin(21, machine.Pin.OUT)
GPO_CardReader_I2C_EN.value(0)      # 還沒有使用過，先不開通

# 娃娃機端的投幣器、電眼配置
GPI_Claw_Coin_IN1 = machine.Pin(16, machine.Pin.IN)
GPI_Claw_Coin_IN2 = machine.Pin(18, machine.Pin.IN)
GPO_Claw_Coin_EN = machine.Pin(5, machine.Pin.OUT)
GPO_Claw_Coin_EN.value(1) # 先直接開通，未來後台決定是否開通投幣器功能
GPO_Claw_CoinPayOUT = machine.Pin(26, machine.Pin.OPEN_DRAIN)
GPO_Claw_CoinPayOUT.value(1)
GPI_Claw_Eyes_IRDIS = machine.Pin(34, machine.Pin.IN)
GPI_Claw_Eyes_IROUT = machine.Pin(35, machine.Pin.IN)
GPI_Claw_Fault_Detect = machine.Pin(39, machine.Pin.IN)

# GPIO 中斷配置
# 設定TV-1QR PAYOUT中斷，觸發條件為正緣和負緣
GPIO_CardReader_PAYOUT.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
GPI_Claw_Coin_IN1.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
GPI_Claw_Coin_IN2.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
GPI_Claw_Eyes_IROUT.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
# GPI_Claw_Fault_Detect.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)

# 創建狀態機
now_main_state = MainStateMachine()
# 創建娃娃機資料
analog_claw_1 = analogClawData()

# 創建 MachMeter 物件
try:
    print("正在初始化 MachMeter...")
    meter = MachMeter()
    print("初始值:", meter.get_all_data())
    analog_claw_1.Number_of_Coin  = meter.get_in()
    analog_claw_1.Number_of_Award = meter.get_out()
    analog_claw_1.Number_of_Original_Payment = meter.get_epay()
    analog_claw_1.Number_of_Free_Payment     = meter.get_fplay()
    analog_claw_1.Error_Code_of_Machine = 0
except Exception as e:
    print('MachMeter init Error:', e)
    analog_claw_1.Error_Code_of_Machine = 23
    
LCD_update_flag['Claw_Value'] = True
LCD_update_flag['Claw_State'] = True

 # 第一次偵測娃娃機是否故障
Fault_Detect_value = GPI_Claw_Fault_Detect.value()
print("Fault_Detect:", Fault_Detect_value)
GPIO_Setting_Coin_and_CardReader(Fault_Detect_value)
Fault_Detect_last_value = Fault_Detect_value


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
            if my_internet_data is not None:
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
