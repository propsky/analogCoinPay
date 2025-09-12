import utime
import os
from machine import SPI, Pin, WDT
import network
import ntptime
from BN165DKBDriver import readKBData
import machine
#　lcd 模組
from lcd_manager import LCDManager
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

# GPIO配置:LCD的背光配置和啟動背光
LCD_EN = machine.Pin(27, machine.Pin.OUT)
LCD_EN.value(1)

# 把st7735所有相關的模組都寫在lcd_manager
# 獲取 LCD 單例singleton
lcd_mgr = LCDManager.get_instance() 
# LCD單例初始化
lcd_mgr.initialize()
lcd_mgr.fill()  # 使用預設顏色（黑色）
# 繪製文字
lcd_mgr.draw_text(0, 0, fg=lcd_mgr.color.WHITE, bg=lcd_mgr.color.BLUE, bgmode=-1) 
#bgmode預設是0 ==>使用預設的bgcolor 例如:.fill()所指定的
#bgmode預設是-1 ==>使用當前參數所指定的bgcolor bg=lcd_mgr.color.BLUE
lcd_mgr.show()

gc.collect()
print(gc.mem_free())

def UDP_Load_Wifi():
    try:
        import usocket as socket
    except:
        import socket
    lcd_mgr.draw_text(0, 16,text='wait UDP Wi-Fi.', fg=lcd_mgr.color.WHITE, bg=lcd_mgr.color.BLACK, bgmode=-1) 
    lcd_mgr.show()
    # Connect to Wi-Fi
    wifi_ssid = "Sam"
    wifi_password = "0928666624"

    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(wifi_ssid, wifi_password)

    while not station.isconnected():
        utime.sleep_ms(200)

    print("Connected to Wi-Fi")
    print('\nConnected. Network config: ', station.ifconfig())
    lcd_mgr.draw_text(0, 32, text='UDP Wi-Fi OK')
    lcd_mgr.draw_text(0, 48, text='IP:') 
    lcd_mgr.draw_text(3, 64, text=station.ifconfig()[0]) 
    lcd_mgr.show()

    # Set up UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("0.0.0.0", 1234))

    print("Listening for UDP messages on port 1234")
    lcd_mgr.draw_text(0, 80, text='wait UDP...')
    lcd_mgr.show()

    while True:
        data, addr = udp_socket.recvfrom(1024)
        print("Received message: {}".format(data.decode('utf-8')))
        lcd_mgr.draw_text(0, 96,text=data.decode('utf-8'))
        lcd_mgr.show()
        with open('wifi.dat', "w") as f:
            f.write(data.decode('utf-8'))
        utime.sleep(3)
        machine.reset()


Data_74HC165 = readKBData(1, CP, CE, PL, Q7)
print("74HC165:", Data_74HC165)
if Data_74HC165[3] == 0 :
    print("SW1被按下，結束程式")
    import sys
    sys.exit()
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

# utime.sleep(3)
utime.sleep(60) # for 景新 中華 4G AP
wdt=WDT(timeout=1000*60*5) 

# =============================
# wifi連線
# =============================
wifi_manager = WiFiManager()
network_info = wifi_manager.connect()
#print(f"網路WiFi:{network_info}")

if network_info: #會顯示net work config資料
    signal_strength = wifi_manager.get_signal_strength()
    print("WiFi Signal Strength:", signal_strength, "dBm")
    lcd_mgr.draw_text(0 , 16, text='SSID:')
    lcd_mgr.draw_text(5 * 8 , 16, text=wifi_manager.ssid)
    lcd_mgr.draw_text(0 , 16 * 2, text=network_info['ip'])
    lcd_mgr.show()

else:
    wifi_manager.disconnect()
    print("No Wifi") 
    lcd_mgr.draw_text(0 , 16, text='No Wifi')

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
    file_list = os.listdir()
    print(file_list)
    gc.collect()
    print(gc.mem_free())
    # 檢查檔案是否存在
    if filename in file_list:
        # 在這邊要做讀取OTA列表，然後進行OTA的執行
        print("OTA檔案存在, OTA checking files...")
        lcd_mgr.draw_text(0 , 16 * 3, text="OTAing...")
        lcd_mgr.show()
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
                branch="SP2_HWv1",  # Optional: Defaults to "master"
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
        os.remove(filename)
        machine.reset()
    else:
        lcd_mgr.draw_text(0, 16 * 3 ,text="No OTA")
        lcd_mgr.show()
        print("OTA檔案不存在")

    print("ESP OTA OK")
else:
    print("No wifi, No OTA!!!!")
# =============================
# 運行主程式
# =============================
while True:
    for i in range(3, 0, -1):
        lcd_mgr.draw_text(0, 16 * 3, text=f"CountDown...{str(i)}",bg=lcd_mgr.color.BLACK, bgmode=-1)
        lcd_mgr.show()
        utime.sleep(1)

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
