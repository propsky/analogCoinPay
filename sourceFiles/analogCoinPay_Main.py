VERSION = "SP2_V0.0825sd_AI_THERMAL"

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
                    # 關掉卡機電源和刷卡功能
                    GPO_CardReader_EPAY_EN.value(0)
                    GPO_CardReader_PAYINOUT_EN.value(0)
                    GPO_CardReader_I2C_EN.value(0)
                    # 關掉投幣器電源
                    GPO_Claw_Coin_EN.value(0)
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

# ===== 診斷日志系統 (非阻塞版本) =====
diagnostic_log_buffer = []  # 日志緩衝區
MAX_LOG_BUFFER_SIZE = 10   # 最大緩衝10條日志

def safe_time_diff(newer_time, older_time):
    """安全的時間差計算，處理ESP32溢出問題"""
    return utime.ticks_diff(newer_time, older_time)

def queue_diagnostic_log(event_type, pin_name, pulse_data=None, result="", reason=""):
    """將診斷日志加入緩衝區（中斷安全，非阻塞）"""
    global diagnostic_log_buffer
    
    # 快速檢查，避免不必要的處理
    if now_main_state.state != MainStatus.STANDBY_MQTT:
        return
    
    try:
        # 構建日志數據（最小化處理時間）
        log_entry = {
            "event": event_type,
            "pin": pin_name,
            "timestamp": utime.time(),
            "uptime_ms": utime.ticks_ms(),
            "result": result,
            "reason": reason
        }
        
        # 如果有脈波數據，加入詳細信息
        if pulse_data:
            log_entry.update(pulse_data)
        
        # 加入緩衝區（如果滿了，移除最舊的）
        if len(diagnostic_log_buffer) >= MAX_LOG_BUFFER_SIZE:
            diagnostic_log_buffer.pop(0)  # 移除最舊的日志
        
        diagnostic_log_buffer.append(log_entry)
        
        # 簡單的本地日志（快速）
        print(f"LOG: {event_type}-{pin_name}-{result}")
        
    except Exception as e:
        # 中斷中不能有複雜的錯誤處理
        pass

def process_diagnostic_log_buffer():
    """在主循環中處理緩衝的日志（非中斷環境）"""
    global diagnostic_log_buffer, mq_client_1
    
    # 只在MQTT連接正常且有日志時處理
    if now_main_state.state != MainStatus.STANDBY_MQTT or not diagnostic_log_buffer:
        return
    
    try:
        # 批量處理，提高效率
        logs_to_send = diagnostic_log_buffer[:5]  # 一次最多處理5條
        diagnostic_log_buffer = diagnostic_log_buffer[5:]  # 移除已處理的
        
        macid = my_internet_data.mac_address
        mq_topic = macid + '/' + token + '/diagnostic'
        
        for log_entry in logs_to_send:
            try:
                mq_json_str = ujson.dumps(log_entry)
                publish_data(mq_client_1, mq_topic, mq_json_str)
                utime.sleep_ms(10)  # 小延遲避免網路壅塞
            except Exception as e:
                print(f"診斷日志發送失敗: {e}")
                break  # 如果發送失敗，停止處理後續日志
                
    except Exception as e:
        print(f"日志緩衝處理錯誤: {e}")
        diagnostic_log_buffer.clear()  # 清空緩衝區避免錯誤累積

# ===== 溫度監控與熱效應診斷 =====
import esp32

def get_internal_temperature():
    """讀取ESP32內建溫度感測器"""
    try:
        # ESP32內建溫度感測器（攝氏度）
        temp_fahrenheit = esp32.raw_temperature()
        temp_celsius = (temp_fahrenheit - 32) * 5.0 / 9.0
        return round(temp_celsius, 1)
    except Exception as e:
        print(f"溫度讀取失敗: {e}")
        return None

def analyze_thermal_impact(pulse_data, temperature):
    """分析溫度對脈波的影響"""
    thermal_analysis = {
        "temperature_c": temperature,
        "thermal_status": "NORMAL"
    }
    
    if temperature is None:
        return thermal_analysis
    
    # 溫度警告閾值
    if temperature > 70:
        thermal_analysis["thermal_status"] = "OVERHEAT_CRITICAL"
        thermal_analysis["thermal_warning"] = "ESP32溫度過高，可能影響時序準確性"
    elif temperature > 60:
        thermal_analysis["thermal_status"] = "OVERHEAT_WARNING" 
        thermal_analysis["thermal_warning"] = "溫度偏高，建議檢查散熱"
    elif temperature < 10:
        thermal_analysis["thermal_status"] = "UNDERHEAT"
        thermal_analysis["thermal_warning"] = "溫度過低，可能影響機械動作"
    
    # 溫度補償建議（基於實驗數據調整）
    if temperature > 50:
        # 高溫時脈波可能變短，建議放寬下限
        suggested_adjustment = int((temperature - 50) * 0.5)  # 每10度放寬0.5ms
        thermal_analysis["temp_compensation"] = f"建議放寬脈波下限{suggested_adjustment}ms"
    
    return thermal_analysis

def queue_thermal_diagnostic_log(event_type, pin_name, pulse_data=None, result="", reason=""):
    """增強版診斷日志，包含溫度資訊"""
    global diagnostic_log_buffer
    
    if now_main_state.state != MainStatus.STANDBY_MQTT:
        return
    
    try:
        # 讀取溫度
        temperature = get_internal_temperature()
        
        log_entry = {
            "event": event_type,
            "pin": pin_name,
            "timestamp": utime.time(),
            "uptime_ms": utime.ticks_ms(),
            "result": result,
            "reason": reason
        }
        
        # 加入溫度資訊
        if temperature is not None:
            thermal_info = analyze_thermal_impact(pulse_data, temperature)
            log_entry.update(thermal_info)
        
        # 加入脈波數據
        if pulse_data:
            log_entry.update(pulse_data)
        
        # 緩衝區管理
        if len(diagnostic_log_buffer) >= MAX_LOG_BUFFER_SIZE:
            diagnostic_log_buffer.pop(0)
        
        diagnostic_log_buffer.append(log_entry)
        
        # 溫度異常時的本地警告
        if temperature and temperature > 65:
            print(f"⚠️ 溫度警告: {temperature}°C - {event_type}-{pin_name}-{result}")
        else:
            print(f"LOG: {event_type}-{pin_name}-{result} (T:{temperature}°C)")
        
    except Exception as e:
        pass

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
            thermal_monitor_callback()  # 溫度監控

        except OSError as e:
            print("3t error:", e)
        utime.sleep_ms(500)                         # 休眠一小段時間，避免過度使用CPU資源

# ===== 溫度監控回調函式 =====
thermal_report_counter = 0
last_reported_temp = None

def thermal_monitor_callback():
    """定期溫度監控與異常報告"""
    global thermal_report_counter, last_reported_temp
    
    thermal_report_counter += 1
    
    # 每30秒檢測一次溫度（server_check每秒執行一次）
    if thermal_report_counter >= 30:
        thermal_report_counter = 0
        
        current_temp = get_internal_temperature()
        if current_temp is None:
            return
        
        # 溫度變化超過5度，或超過警告閾值時立即報告
        temp_changed = (last_reported_temp is None or 
                       abs(current_temp - last_reported_temp) >= 5.0)
        temp_warning = current_temp > 60 or current_temp < 10
        
        if temp_changed or temp_warning:
            last_reported_temp = current_temp
            
            # 發送溫度監控日志
            temp_log = {
                "event": "thermal_monitor",
                "pin": "ESP32_INTERNAL", 
                "temperature_c": current_temp,
                "thermal_status": "NORMAL",
                "uptime_hours": round(utime.ticks_ms() / 3600000, 1)
            }
            
            if current_temp > 70:
                temp_log["thermal_status"] = "OVERHEAT_CRITICAL"
                temp_log["reason"] = "ESP32過熱，可能影響系統穩定性"
                print(f"🚨 嚴重過熱警告: {current_temp}°C")
            elif current_temp > 60:
                temp_log["thermal_status"] = "OVERHEAT_WARNING"
                temp_log["reason"] = "溫度偏高，建議檢查散熱系統"
                print(f"⚠️ 過熱警告: {current_temp}°C")
            elif current_temp < 10:
                temp_log["thermal_status"] = "UNDERHEAT"
                temp_log["reason"] = "溫度過低，可能影響機械動作"
            else:
                temp_log["reason"] = "溫度正常範圍"
            
            # 加入緩衝區
            if len(diagnostic_log_buffer) >= MAX_LOG_BUFFER_SIZE:
                diagnostic_log_buffer.pop(0)
            diagnostic_log_buffer.append(temp_log)

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
Eyes_IRDIS_last_falling_time = utime.ticks_ms()
Eyes_IRDIS_last_rising_time = utime.ticks_ms()
Eyes_IROUT_last_falling_time = utime.ticks_ms()
Eyes_IROUT_last_rising_time = utime.ticks_ms()
Is_FEILOLI_eyes = 0
PAYOUT_last_value = -1      # -1 代表未知狀態
Coin_IN1_last_value = -1    # -1 代表未知狀態
Coin_IN2_last_value = -1    # -1 代表未知狀態
def GPI_interrupt_handler(pin):
    if pin == GPIO_CardReader_PAYOUT :
        global PAYOUT_last_falling_time, PAYOUT_last_rising_time, PAYOUT_last_value
        PAYOUT_value = GPIO_CardReader_PAYOUT.value()
        PAYOUT_now_time = utime.ticks_ms()
        if PAYOUT_last_value != PAYOUT_value :
            PAYOUT_last_value = PAYOUT_value
            print("PAYOUT收到中斷和變化:", PAYOUT_value)
            
            # 記錄中斷事件（非阻塞）
            queue_diagnostic_log("interrupt", "PAYOUT", 
                               {"gpio_value": PAYOUT_value, "interrupt_time": PAYOUT_now_time})
            
            if PAYOUT_value == 0 :      # 1->0
                PAYOUT_last_falling_time = PAYOUT_now_time
            elif PAYOUT_value == 1 :    # 0->1
                PAYOUT_rising_time = PAYOUT_now_time
                # 使用安全的時間差計算
                PAYOUT_hipulse_time = safe_time_diff(PAYOUT_last_falling_time, PAYOUT_last_rising_time)
                PAYOUT_lowpulse_time = safe_time_diff(PAYOUT_rising_time, PAYOUT_last_falling_time)
                print("中斷PAYOUT收到Hi Pulse寬度(ms):", PAYOUT_hipulse_time, ",和Low Pulse寬度(ms):", PAYOUT_lowpulse_time)
                
                # 準備脈波數據用於診斷
                pulse_data = {
                    "hi_pulse_ms": PAYOUT_hipulse_time,
                    "low_pulse_ms": PAYOUT_lowpulse_time,
                    "hi_pulse_min": 100,
                    "low_pulse_min": 50,
                    "low_pulse_max": 200
                }
                
                # 判斷脈波寬度是否符合要求
                hi_pulse_ok = PAYOUT_hipulse_time >= 100
                low_pulse_ok = (50 <= PAYOUT_lowpulse_time <= 200)
                
                if hi_pulse_ok and low_pulse_ok:
                    print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲。")
                    global Rounds_of_Starting_games
                    Rounds_of_Starting_games = Rounds_of_Starting_games + 1
                    analog_claw_1.Number_of_Original_Payment = meter.inc_epay()
                    meter.save()
                    LCD_update_flag['Claw_Value'] = True
                    
                    # 記錄成功的脈波（非阻塞，含溫度）
                    queue_thermal_diagnostic_log("card_pulse", "PAYOUT", pulse_data, "ACCEPTED", "脈波寬度符合要求")
                else :
                    print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
                    
                    # 分析具體的拒絕原因
                    reasons = []
                    if not hi_pulse_ok:
                        reasons.append(f"Hi脈波過短({PAYOUT_hipulse_time}ms < 100ms)")
                    if not low_pulse_ok:
                        if PAYOUT_lowpulse_time < 50:
                            reasons.append(f"Low脈波過短({PAYOUT_lowpulse_time}ms < 50ms)")
                        elif PAYOUT_lowpulse_time > 200:
                            reasons.append(f"Low脈波過長({PAYOUT_lowpulse_time}ms > 200ms)")
                    
                    reason_str = "; ".join(reasons)
                    queue_thermal_diagnostic_log("card_pulse", "PAYOUT", pulse_data, "REJECTED", reason_str)
                    
                PAYOUT_last_rising_time = PAYOUT_rising_time
    
    if pin == GPI_Claw_Coin_IN1 :
        global Coin_IN1_last_falling_time, Coin_IN1_last_rising_time, Coin_IN1_last_value
        Coin_IN1_value = GPI_Claw_Coin_IN1.value()
        Coin_IN1_now_time = utime.ticks_ms()
        if Coin_IN1_last_value != Coin_IN1_value :
            Coin_IN1_last_value = Coin_IN1_value
            print("Coin_IN1收到中斷和變化:", Coin_IN1_value)
            
            # 記錄中斷事件（非阻塞）
            queue_diagnostic_log("interrupt", "Coin_IN1", 
                               {"gpio_value": Coin_IN1_value, "interrupt_time": Coin_IN1_now_time})
            
            if Coin_IN1_value == 0 :      # 1->0
                Coin_IN1_last_falling_time = Coin_IN1_now_time
            elif Coin_IN1_value == 1 :    # 0->1
                Coin_IN1_rising_time = Coin_IN1_now_time
                # 使用安全的時間差計算
                Coin_IN1_hipulse_time = safe_time_diff(Coin_IN1_last_falling_time, Coin_IN1_last_rising_time)
                Coin_IN1_lowpulse_time = safe_time_diff(Coin_IN1_rising_time, Coin_IN1_last_falling_time)
                print("中斷Coin_IN1收到Hi Pulse寬度(ms):", Coin_IN1_hipulse_time, ",和Low Pulse寬度(ms):", Coin_IN1_lowpulse_time)
                
                # 準備脈波數據用於診斷
                pulse_data = {
                    "hi_pulse_ms": Coin_IN1_hipulse_time,
                    "low_pulse_ms": Coin_IN1_lowpulse_time,
                    "hi_pulse_min": 100,
                    "low_pulse_min": 10,
                    "low_pulse_max": 200
                }
                
                # 判斷脈波寬度是否符合要求
                hi_pulse_ok = Coin_IN1_hipulse_time >= 100
                low_pulse_ok = (10 <= Coin_IN1_lowpulse_time <= 200)
                
                if hi_pulse_ok and low_pulse_ok:
                    print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲")
                    global Rounds_of_Starting_games
                    Rounds_of_Starting_games = Rounds_of_Starting_games + 1
                    analog_claw_1.Number_of_Coin = meter.inc_in()
                    meter.save()
                    LCD_update_flag['Claw_Value'] = True
                    
                    # 記錄成功的脈波（非阻塞，含溫度）
                    queue_thermal_diagnostic_log("coin_pulse", "Coin_IN1", pulse_data, "ACCEPTED", "脈波寬度符合要求")
                else :
                    print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
                    
                    # 分析具體的拒絕原因
                    reasons = []
                    if not hi_pulse_ok:
                        reasons.append(f"Hi脈波過短({Coin_IN1_hipulse_time}ms < 100ms)")
                    if not low_pulse_ok:
                        if Coin_IN1_lowpulse_time < 10:
                            reasons.append(f"Low脈波過短({Coin_IN1_lowpulse_time}ms < 10ms)")
                        elif Coin_IN1_lowpulse_time > 200:
                            reasons.append(f"Low脈波過長({Coin_IN1_lowpulse_time}ms > 200ms)")
                    
                    reason_str = "; ".join(reasons)
                    queue_thermal_diagnostic_log("coin_pulse", "Coin_IN1", pulse_data, "REJECTED", reason_str)
                    
                Coin_IN1_last_rising_time = Coin_IN1_rising_time
    
    if pin == GPI_Claw_Coin_IN2 :
        global Coin_IN2_last_falling_time, Coin_IN2_last_rising_time, Coin_IN2_last_value
        Coin_IN2_value = GPI_Claw_Coin_IN2.value()
        Coin_IN2_now_time = utime.ticks_ms()
        if Coin_IN2_last_value != Coin_IN2_value :
            Coin_IN2_last_value = Coin_IN2_value
            print("Coin_IN2收到中斷和變化:", Coin_IN2_value)
            
            # 記錄中斷事件（非阻塞）
            queue_diagnostic_log("interrupt", "Coin_IN2", 
                               {"gpio_value": Coin_IN2_value, "interrupt_time": Coin_IN2_now_time})
            
            if Coin_IN2_value == 0 :      # 1->0
                Coin_IN2_last_falling_time = Coin_IN2_now_time
            elif Coin_IN2_value == 1 :    # 0->1
                Coin_IN2_rising_time = Coin_IN2_now_time
                # 使用安全的時間差計算
                Coin_IN2_hipulse_time = safe_time_diff(Coin_IN2_last_falling_time, Coin_IN2_last_rising_time)
                Coin_IN2_lowpulse_time = safe_time_diff(Coin_IN2_rising_time, Coin_IN2_last_falling_time)
                print("中斷Coin_IN2收到Hi Pulse寬度(ms):", Coin_IN2_hipulse_time, ",和Low Pulse寬度(ms):", Coin_IN2_lowpulse_time)
                
                # 準備脈波數據用於診斷
                pulse_data = {
                    "hi_pulse_ms": Coin_IN2_hipulse_time,
                    "low_pulse_ms": Coin_IN2_lowpulse_time,
                    "hi_pulse_min": 100,
                    "low_pulse_min": 10,
                    "low_pulse_max": 200
                }
                
                # 判斷脈波寬度是否符合要求
                hi_pulse_ok = Coin_IN2_hipulse_time >= 100
                low_pulse_ok = (10 <= Coin_IN2_lowpulse_time <= 200)
                
                if hi_pulse_ok and low_pulse_ok:
                    print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲")
                    global Rounds_of_Starting_games
                    Rounds_of_Starting_games = Rounds_of_Starting_games + 1
                    analog_claw_1.Number_of_Coin = meter.inc_in()
                    meter.save()
                    LCD_update_flag['Claw_Value'] = True
                    
                    # 記錄成功的脈波（非阻塞，含溫度）
                    queue_thermal_diagnostic_log("coin_pulse", "Coin_IN2", pulse_data, "ACCEPTED", "脈波寬度符合要求")
                else :
                    print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
                    
                    # 分析具體的拒絕原因
                    reasons = []
                    if not hi_pulse_ok:
                        reasons.append(f"Hi脈波過短({Coin_IN2_hipulse_time}ms < 100ms)")
                    if not low_pulse_ok:
                        if Coin_IN2_lowpulse_time < 10:
                            reasons.append(f"Low脈波過短({Coin_IN2_lowpulse_time}ms < 10ms)")
                        elif Coin_IN2_lowpulse_time > 200:
                            reasons.append(f"Low脈波過長({Coin_IN2_lowpulse_time}ms > 200ms)")
                    
                    reason_str = "; ".join(reasons)
                    queue_thermal_diagnostic_log("coin_pulse", "Coin_IN2", pulse_data, "REJECTED", reason_str)
                    
                Coin_IN2_last_rising_time = Coin_IN2_rising_time
    
    if pin == GPI_Claw_Eyes_IRDIS :
        global Eyes_IRDIS_last_falling_time, Eyes_IRDIS_last_rising_time, Is_FEILOLI_eyes
        Eyes_IRDIS_value = GPI_Claw_Eyes_IRDIS.value()
        Eyes_IRDIS_now_time = utime.ticks_ms()
        print("Eyes_IRDIS_收到中斷:", Eyes_IRDIS_value)
        if Eyes_IRDIS_value == 0 :      # 1->0
            Eyes_IRDIS_last_falling_time = Eyes_IRDIS_now_time
        elif Eyes_IRDIS_value == 1 :    # 0->1
            Is_FEILOLI_eyes = 1         # IRDIS曾經拉Hi，代表這是飛絡力電眼
            Eyes_IRDIS_last_rising_time = Eyes_IRDIS_now_time
    
    if pin == GPI_Claw_Eyes_IROUT :
        global Eyes_IROUT_last_falling_time, Eyes_IROUT_last_rising_time, Is_FEILOLI_eyes, Eyes_IRDIS_last_rising_time
        Eyes_IROUT_value = GPI_Claw_Eyes_IROUT.value()
        Eyes_IROUT_now_time = utime.ticks_ms()
        print("Eyes_IROUT收到中斷:", Eyes_IROUT_value)
        if Eyes_IROUT_value == 0 :      # 1->0
            Eyes_IROUT_falling_time = Eyes_IROUT_now_time
            if  Is_FEILOLI_eyes == 0 :
                Eyes_IROUT_lowpulse_time = Eyes_IROUT_last_rising_time - Eyes_IROUT_last_falling_time
                Eyes_IROUT_hipulse_time = Eyes_IROUT_falling_time - Eyes_IROUT_last_rising_time
                print("中斷Eyes_IROUT收到Low Pulse寬度(ms):", Eyes_IROUT_lowpulse_time, ",和Hi Pulse寬度(ms):", Eyes_IROUT_hipulse_time)
                if Eyes_IROUT_lowpulse_time >= 1000 and (10 <= Eyes_IROUT_hipulse_time and Eyes_IROUT_hipulse_time <=800) :
                    print("通用電眼Low Pulse->Hi Pulse，寬度都正確，出獎+1")
                    analog_claw_1.Number_of_Award = meter.inc_out()
                    meter.save()
                    LCD_update_flag['Claw_Value'] = True
                else :
                    print("通用電眼Low Pulse->Hi Pulse，寬度不正確，不進行任何動作")
            Eyes_IROUT_last_falling_time = Eyes_IROUT_falling_time
        elif Eyes_IROUT_value == 1 :    # 0->1
            Eyes_IROUT_rising_time = Eyes_IROUT_now_time
            Eyes_Enable_time = Eyes_IROUT_last_falling_time - Eyes_IRDIS_last_rising_time
            Eyes_IROUT_hipulse_time = Eyes_IROUT_last_falling_time - Eyes_IROUT_last_rising_time
            Eyes_IROUT_lowpulse_time = Eyes_IROUT_rising_time - Eyes_IROUT_last_falling_time
            print("中斷Eyes_IROUT收到Hi Pulse寬度(ms):", Eyes_IROUT_hipulse_time, ",和Low Pulse寬度(ms):", Eyes_IROUT_lowpulse_time)
            if Eyes_Enable_time >= 1000 and Eyes_IROUT_hipulse_time >= 1000 and (10 <= Eyes_IROUT_lowpulse_time and Eyes_IROUT_lowpulse_time <=800) : # 測試出飛絡力800ms以內算出獎
                print("出表或飛絡力/通用電眼Hi Pulse->Low Pulse，寬度和致能時間都正確，出獎+1")
                analog_claw_1.Number_of_Award = meter.inc_out()
                meter.save()
                LCD_update_flag['Claw_Value'] = True
            else :
                print("出表或飛絡力/通用電眼Hi Pulse->Low Pulse，寬度或致能時間不正確，不進行任何動作")
            Eyes_IROUT_last_rising_time = Eyes_IROUT_rising_time
       

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

# 檢查GPIO初始值
PAYOUT_last_value = GPIO_CardReader_PAYOUT.value()
Coin_IN1_last_value = GPI_Claw_Coin_IN1.value()
Coin_IN2_last_value = GPI_Claw_Coin_IN2.value()
Eyes_IRDIS_value = GPI_Claw_Eyes_IRDIS.value()
if Eyes_IRDIS_value == 1 :
    Is_FEILOLI_eyes = 1         # IRDIS曾經拉Hi，代表這是飛絡力電眼
print(f"Init GPIO配置: PAYOUT, Coin_IN1, Coin_IN2, Eyes_IRDIS, Is_FEILOLI_eyes")
print(f"Read value: {PAYOUT_last_value}, {Coin_IN1_last_value}, {Coin_IN2_last_value}, {Eyes_IRDIS_value}, {Is_FEILOLI_eyes}" )

# GPIO 中斷配置
# 設定TV-1QR PAYOUT中斷，觸發條件為正緣和負緣
GPIO_CardReader_PAYOUT.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
GPI_Claw_Coin_IN1.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
GPI_Claw_Coin_IN2.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
GPI_Claw_Eyes_IRDIS.irq(trigger = ( machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING ), handler = GPI_interrupt_handler)
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

    # 處理診斷日志緩衝（非阻塞，在主循環中執行）
    process_diagnostic_log_buffer()

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
