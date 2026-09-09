import utime
import uos
import ujson
import gc
from machine import Pin, WDT
import network
import ntptime
from BN165DKBDriver import readKBData
import machine
# RGB LED 狀態燈模組（SP3 移除 LCD 後改用）
from rgb_led_manager import RGBLEDManager
from wifimgr import WiFiManager

# GPIO配置:卡機端的TV-1配置，關掉卡機電源和刷卡功能
GPO_CardReader_EPAY_EN = machine.Pin(2, machine.Pin.OUT)
GPO_CardReader_EPAY_EN.value(0)
GPO_CardReader_PAYINOUT_EN = machine.Pin(19, machine.Pin.OUT)
GPO_CardReader_PAYINOUT_EN.value(0)
GPO_CardReader_I2C_EN = machine.Pin(21, machine.Pin.OUT)
GPO_CardReader_I2C_EN.value(0)

# GPIO配置:娃娃機端的投幣器電源配置，關掉投幣器電源
GPO_Claw_Coin_EN = machine.Pin(5, machine.Pin.OUT)
GPO_Claw_Coin_EN.value(0)

# GPIO配置:74HC165的四個IO線配置和UDP-WiFi設定板的一個IO配置
CP = Pin(0, Pin.OUT)
CE = Pin(0, Pin.OUT)
PL = Pin(32, Pin.OUT)
Q7 = Pin(33, Pin.IN)
ESP32_TXD2_FEILOLI = Pin(17, Pin.IN)

# GPIO27 原為 LCD_EN 背光致能；SP3 移除 LCD 後，此腳改給 WS2812 狀態燈（見 rgb_led_manager）

# 取得 RGB LED 單例並初始化：先跑上電自檢(紅→綠→藍)，再進入開機中(白呼吸)
led_mgr = RGBLEDManager.get_instance()
led_mgr.initialize()        # 預設 pin=27, num=1, brightness=25
led_mgr.boot_test()         # 紅→綠→藍 各 500ms，阻塞 1500ms
led_mgr.set_state(RGBLEDManager.BOOTING)

gc.collect()
print(gc.mem_free())

def UDP_Load_Wifi():
    try:
        import usocket as socket
    except:
        import socket
    led_mgr.set_state(RGBLEDManager.WIFI_CONFIG)   # UDP 設定模式：水藍呼吸
    # Connect to Wi-Fi
    wifi_ssid = "Sam"
    wifi_password = "0928666624"

    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(wifi_ssid, wifi_password)

    while not station.isconnected():
        led_mgr.tick()             # 等待連線期間推進燈效，否則呼吸會凍住
        utime.sleep_ms(50)

    print("Connected to Wi-Fi")
    print('\nConnected. Network config: ', station.ifconfig())

    # Set up UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("0.0.0.0", 1234))

    print("Listening for UDP messages on port 1234")

    while True:
        data, addr = udp_socket.recvfrom(1024)
        print("Received message: {}".format(data.decode('utf-8')))
        with open('wifi.dat', "w") as f:
            f.write(data.decode('utf-8'))
        utime.sleep(3)
        machine.reset()


Data_74HC165 = readKBData(1, CP, CE, PL, Q7)
print("74HC165:", Data_74HC165)
if Data_74HC165[3] == 0 :
    print("SW1被按下，停止程式並進入 REPL（可推檔/下指令）")
    led_mgr.set_state(RGBLEDManager.STOPPED)   # SW1 停止：紅恆亮（此處在 WDT 建立之前，無看門狗）
    gc.collect()                               # 回收 setup 暫時物件，進 REPL 後多點可用 RAM
    # 丟一般例外(KeyboardInterrupt)中止 main.py → 掉 REPL 等待畫面。
    # 註：1.29 的 sys.exit()/SystemExit 會被當 forced-exit 觸發 soft reset → 重開迴圈，故不用它。
    raise KeyboardInterrupt
elif Data_74HC165[0] == 0 :
    from mach_meter import MachMeter
    print("正在初始化 MachMeter，並且歸零。")
    meter = MachMeter()
    meter.reset_all_data()
    meter.save()
    print("SW4被按下，進入UDP load wifi")
    UDP_Load_Wifi()
elif ESP32_TXD2_FEILOLI.value() == 0 :
    print("ESP32_TXD2_FEILOLI被拉Low，進入UDP load wifi")
    UDP_Load_Wifi()

wdt=WDT(timeout=1000*60*5) 

def read_boot_delay():
    default_delay = 3
    config_file = 'config.json'
    try:
        if config_file not in uos.listdir():
            print(f"配置檔案 {config_file} 不存在，使用預設值")
            return default_delay
        
        with open(config_file, 'r') as f:
            config = ujson.load(f)
            print(f"讀取配置檔案 {config_file} 成功")
            
        if 'boot_delay_sec' in config:
            delay = config['boot_delay_sec']
            if isinstance(delay, int): # 檢查是否為整數
                if 1 <= delay <= 300:  # 限制在 1-300 秒範圍內
                    print(f"從配置檔案讀取到開機延遲: {delay} 秒")
                    return delay
                else:
                    print(f"延遲時間 {delay} 秒超出合理範圍 (1-300)，使用預設值")
                    return default_delay
            else:
                print(f"delay值不是整數: {delay}，使用預設值")
                return default_delay
        else:
            print("配置檔案中沒有找到 'boot_delay_sec' 欄位，使用預設值")
            return default_delay
        
    except ujson.JSONDecodeError as e:
        print(f"JSON格式錯誤: {e}，使用預設值")
        return default_delay
    except Exception as e:
        print(f"讀取配置檔案時發生錯誤: {e}，使用預設值")
        return default_delay

# 讀取開機延遲設定
delay_seconds = read_boot_delay()
# 執行延遲：改成 50ms 分段並推進燈效，期間維持 BOOTING(白呼吸)；否則呼吸會凍在第一幀
print(f'開始延遲 {delay_seconds} 秒...')
for _ in range(delay_seconds * 20):   # delay_seconds × 20 段 × 50ms
    led_mgr.tick()
    utime.sleep_ms(50)
print('延遲完成！')

# =============================
# wifi連線
# =============================
wifi_manager = WiFiManager()
# 先無條件設「嘗試連線」(WIFI_CONNECTING 紅呼吸)；若 wifimgr 判定要進 AP 設定模式，
# 會透過 on_ap_mode 回呼把燈改成 WIFI_CONFIG(水藍呼吸)。連線分支判斷只留在 wifimgr 一處。
led_mgr.set_state(RGBLEDManager.WIFI_CONNECTING)
network_info = wifi_manager.connect(
    on_tick=led_mgr.tick,                                            # 等待期間推進燈效
    on_ap_mode=lambda: led_mgr.set_state(RGBLEDManager.WIFI_CONFIG),  # 進 AP 設定模式時轉水藍呼吸
)
#print(f"網路WiFi:{network_info}")

if network_info: #連上 WiFi：接著要等 MQTT，先顯示 NO_MQTT(黃閃2下)
    signal_strength = wifi_manager.get_signal_strength()
    print("WiFi Signal Strength:", signal_strength, "dBm")
    led_mgr.set_state(RGBLEDManager.NO_MQTT)

else:
    wifi_manager.disconnect()
    print("No Wifi")
    led_mgr.set_state(RGBLEDManager.NO_WIFI)          # 重試 10 次皆失敗：紅閃1下(確定連不上)

print("ESP Wi-Fi OK")
gc.collect()
print(gc.mem_free())    

# =============================
# NTP伺服器與時間處理
# =============================
# # 增加多個NTP伺服器選項(失敗就會跳下一個嘗試)
def tw_ntp(must=False):
    ntp_servers = [
        "clock.stdtime.gov.tw", 
        "time.stdtime.gov.tw",
        "watch.stdtime.gov.tw", 
        "tick.stdtime.gov.tw", 
        "pool.ntp.org",  # 全球可用 NTP 伺服器 test ok
        "time.google.com" #Google NTP 伺服器，全球適用 
    ]  
    ntptime.NTP_DELTA = 3155673600 # UTC+8 的 magic number
    #3155673600 秒 = UTC+8 的時間修正值（因為 MicroPython 預設 NTP 是 UTC 1970 年）
    #count = 1 if not must else 10 #最多嘗試10次

    #for _ in  range(count):
    for server in ntp_servers:
        try:
            ntptime.host = server # 調整時間的基準值
            ntptime.settime() #設定timeout 
            print(f"NTP 時間同步成功，使用 {server}")
            return True
        except Exception as e:
            print(f"嘗試 {server} 失敗: {e}")
            utime.sleep(1)
            continue  # 不 return False，繼續嘗試下一個伺服器
    print("所有 NTP 伺服器皆無法同步，改用 HTTP 時間")
    # 用http做時間同步的備援
    wifi_manager.get_http_time()


#這裡待做斷網測試 2025/05/05已加上
if network_info:
    tw_ntp(must=True) # Thomas發現must沒有作用
    print("ESP NTP Time OK")

    # =============================
    # OTA更新相關
    # =============================
    # 檔案名稱
    filename = 'otalist.dat'

    # 取得目錄下的所有檔案和資料夾
    file_list = uos.listdir()
    print(file_list)
    gc.collect()
    print(gc.mem_free())
    # 檢查檔案是否存在
    if filename in file_list:
        # 在這邊要做讀取OTA列表，然後進行OTA的執行
        print("OTA檔案存在, OTA checking files...")
        led_mgr.set_state(RGBLEDManager.UPDATING_REBOOTING, lock=True)   # OTA 進行中：白恆亮
        try:
            with open(filename) as f:
                lines = f.readlines()[0].strip()

            lines = lines.replace(' ', '')
            # 移除字串中的雙引號和空格，然後使用逗號分隔字串
            file_list = [file.strip('"') for file in lines.split(',')]

            import senko
            OTA = senko.Senko(
                user="propsky",  # Required
                repo="analogCoinPay",  # Required
                branch="SP3_HWv2.1",  # Optional: Defaults to "master"
                working_dir="releaseFiles/latestVersion",  # Optional: Defaults to "app"
                files=file_list
            )

            gc.collect()
            print(gc.mem_free())
            if OTA.update():
                print("Updated to the latest version!")
            else:
                print("Cannot find new-changed files for OTA, or check error")
        except Exception as e:
            print(f"Updated error:{e}")

        print("刪除OTA檔案, rebooting...")
        uos.remove(filename)
        machine.reset()
    else:
        print("OTA檔案不存在")

    print("ESP OTA OK")
else:
    print("No wifi, No OTA!!!!")
# =============================
# 運行主程式
# =============================
while True:
    # 倒數 3 秒進主程式：維持前一狀態的燈號，用 50ms 分段推進燈效
    for i in range(3, 0, -1):
        print(f"CountDown...{i}")
        for _ in range(20):        # 20 × 50ms = 1 秒
            led_mgr.tick()
            utime.sleep_ms(50)

    # import micropython
    gc.collect()
    print(gc.mem_free())
    # micropython.mem_info()
    try:
        print("執行analogCoinPay_Main.py...")
        execfile('analogCoinPay_Main.py')
    except Exception as e:
        print("執行失敗:", e)
        utime.sleep(5)
