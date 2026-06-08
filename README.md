# code-change list

**2026/6/2_SP2_mpy_QR_V0.10a, Thomas**
1. analogCoinPay_Main.py 新增 WiFi QR Code 寫入功能  
a. 新增 `parse_wifi_qr()` 函式：解析 WiFi QR Code 格式（`WIFI:T:<auth>;S:<ssid>;P:<password>;H:<hidden>;;`），驗證為 WPA 加密且 SSID/密碼不為空後，寫入 wifi.dat（格式：`ssid;password\n`），與 wifimgr.py 的 `save_wifi_config()` 格式一致  
b. 修改 `uart_QRScanner_recive_packet_task()`：掃到 WIFI: 開頭時優先呼叫 `parse_wifi_qr()`，成功後執行 `safe_reboot()`；非 WiFi 格式才進入 UUID 36 字元判斷  
c. WiFi QR Code 前綴判斷改為大小寫不敏感（`.upper().startswith("WIFI:")`），相容不同 QR 產生器輸出  
d. 娃娃機故障時仍可接受 WiFi QR Code 寫入（故障檢查只擋 UUID MQTT 發送，不擋 WiFi 設定）  
2. analogCoinPay_Main.py 修正整數除法錯誤  
a. `Error_Code_of_Machine` 計算從 `/`（浮點）改為 `//`（整數），避免後續 `%100`、`*100` 運算型別不一致  
3. main.py 補上缺少的模組導入，並修正 OTA branch 設定  
a. 新增 `import gc`，修正開機時 `gc.collect()` / `gc.mem_free()` 可能因未導入而失敗的問題  
b. OTA branch 從 `"SP2_HWv1"` 改為 `"SP2_HWv1_QR_mpy"`，確保 OTA 從正確的 branch 拉取最新檔案  
4. 修改 to-be-do list  
a. 新增第 8 項：wifimgr.py 跨年日期計算潛在 bug（AI 檢查發現，低優先）  
* Based on SP2_HWv1_QR_mpy 2026/4/15_SP2_mpy_QR_test0415f, Thomas
---
**2026/4/15_SP2_mpy_QR_test0415f, Thomas**
1. analogCoinPay_Main.py 新增 QR Code 掃碼器支援  
a. Pin 21 從 `GPO_CardReader_I2C_EN` 更名為 `GPO_QRScanner_UART_EN`，功能改為 QR 掃碼器 UART 訊號開關，初始值從 0 改為 1（開通）  
b. 新增 UART1 配置：TX=22, RX=23, baudrate=115200  
c. 新增獨立執行緒 `uart_QRScanner_recive_packet_task()` 持續接收掃碼資料  
d. UUID 長度驗證：36字元才有效，否則只印 log，不發送 MQTT  
e. 娃娃機故障或狀態未知（Fault_Detect_last_value != 0）時，忽略掃碼，不發送 MQTT  
f. 更新 GPIO 配置區說明，補充三路訊號開關（EPAY_EN/PAYINOUT_EN/UART_EN）皆為 0 時才切斷卡機TV-1和掃碼器電源的控制邏輯  
2. analogCoinPay_Main.py 新增 MQTT 即時事件封包（events）  
a. 新增全域變數 `server_event_QRScan_flag`、`server_event_QRScan_uuid`  
b. 新增全域變數 `server_event_GiftOut_Count`（計數而非旗標，支援短時間多次出獎累積）  
c. `publish_MQTT_claw_data()` 新增 `events-qrscan` 和 `events-giftout` 兩個分支，Topic: `{macid}/{token}/events`  
d. `server_check_timer_callback()` 新增發送 QRScan 和 GiftOut 事件邏輯  
e. 電眼出獎中斷（`GPI_interrupt_handler`）觸發時，`server_event_GiftOut_Count += 1`（通用電眼和飛絡力電眼兩條路徑皆有）  
3. analogCoinPay_Main.py `safe_reboot()` 更新：`GPO_CardReader_I2C_EN` 更名為 `GPO_QRScanner_UART_EN`，重開機前關閉掃碼器訊號  
4. main.py 更新  
a. Pin 21 從 `GPO_CardReader_I2C_EN` 更名為 `GPO_QRScanner_UART_EN`，開機時保持關閉（value(0)）  
b. 執行主程式邏輯：先 `execfile('analogCoinPay_Main.py')`，失敗則 fallback 到 `__import__('analogCoinPay_Main')` 載入 .mpy  
c. 更新 GPIO 配置區說明：標題從「卡機端的TV-1配置」改為「卡機TV-1和掃碼器端的配置」，並補充三者皆0才切斷電源的邏輯；各 Pin 行新增行內說明  
5. wifi.dat 更新：SSID 改為 TAGE 展場 WiFi（TAGE_propsky）  
6. 部署方式改為 .mpy：analogCoinPay_Main.py 過大（約37KB），ESP32 記憶體不足無法直接執行  
a. 改以 mpy-cross v1.18.0 編譯成 .mpy（約17KB）部署  
b. analogCoinPay_Main.py 新增 `from lcd_manager import LCDManager` import（改為 .mpy 後 main.py 不傳遞 namespace，必須自行 import）  
c. main.py 執行邏輯：先 `execfile('analogCoinPay_Main.py')`，失敗則 `__import__('analogCoinPay_Main')` 載入 .mpy（已含於第 4 項 b）  
d. 刪除 analogCoinPay_Main.py 中不再使用的程式碼與註解以縮減檔案大小：`MainStateMachine.transition()` 中被 `'''` 包住的 MQTT disconnect 處理邏輯（標記為「這作法不順利，先不用」）、`get_file_info()` 中 `# Index 6:file size` 和 `# Index 8:modification time` 行內說明  
7. BN165DKBDriver.py、senko.py：換行格式統一為 Unix（LF），無功能修改  
8. Branch 和版本管理調整  
a. 新增 QR scanner 功能，branch 從 `SP2_HWv1` 轉移到 `SP2_HWv1_QR_mpy`（以 SP2_V0.30b 為基礎修改）  
b. 版本號命名改為 `SP2_mpy_QR_xxxxxxxxxx` 格式  
c. README code-change list 清除 SP2_V0.30b 以前的紀錄，從 SP2_V0.30b 開始保留  
9. 修改 to-be-do list  
* Based on SP2_HWv1 2025/9/17_SP2_V0.30b, Thomas
---
**2025/9/17_SP2_V0.30b, Thomas**
1. analogCoinPay_Main.py 重大更新  
a. 模組導入統一：import os 改為 import uos，符合MicroPython標準  
b. 新增 safe_reboot() 函數：統一的重開機處理機制，先關卡機和投幣器電源，等待3秒後，下重開機指令  
c. 同樣的事情用較短但不難懂的程式碼達成，減少檔案大小  
d. 加速three_timer_task，讓if Rounds_of_Starting_games > 0: GPIO_Send_Starting_games()的檢查間隔時間從0.5秒變成0.2秒  
e. 故障檢測初始化：修改Fault_Detect_last_value初始狀態=-1，直到three_timer_task啟動後才會依造故障狀態開啟卡機和投幣器電源  
f. 語法錯誤修正：修正 Is_FEILOLI_eyes 和 Eyes_IRDIS_last_rising_time 的全域變數宣告位置，統一移到 GPI_interrupt_handler() 函數開頭  
g. 脈衝檢測參數調整：PAYOUT、 Coin_IN1、 Coin_IN2 允許Low脈波時間範圍從 50-200ms 放寬到 5-300ms，Hi持續時間也從100ms放寬到50ms  
h. 刪掉沒用到的sleep註解  
i. 新增定期重開機機制：開機超過3天，並且是早上3點時，進行重開機  
j. while loop狀態機每一個狀態做完都會做gc.collect()  
2. main.py 配置系統重構  
a. 模組導入更新：新增 import uos, ujson，移除 import os  
b. 可配置啟動延遲系統：新增 read_boot_delay() 函數，取代固定60秒延遲  
c. 支援從config.json配置檔案讀取 boot_delay_sec，預設3秒，包含完整錯誤處理機制  
d. 提升開發效率：啟動時間從固定60秒縮短為可配置秒數  
3. senko.py 模組導入統一：import os 改為 import uos，保持與其他檔案一致性  
4. 新增配置檔案  
a. config.json：新的系統配置檔案，支援啟動延遲配置
{
    "boot_delay_sec": 60
}
5. 電腦上原始檔，換行格式修改成Unix(LF)：analogCoinPay_Main.py、config.json、ntptime.py、senko.py
6. 原本就是Unix(LF)，所以不用修改：main.py、wifimgr.py
7. 修改to-be-do list
* Based on smartpay2 9/4_SP2_V0.20a, Thomas
---

# to-be-do list

1. 修補小卡的重連機制，不嘗試連線時，想要完全關掉wifi模組
=> 這樣也能解決main執行時都要延遲一分鐘才能繼續開機

2. 當IO的last_time太大時，自動清除
```python
# 在10秒檢查迴圈中
if GPI_Claw_Coin_IN1.value() == 1:  # 投幣器待機(高電平)
    current_time = utime.ticks_ms()
    time_since_last_rising = utime.ticks_diff(current_time, Coin_IN1_last_rising_time)
    
    if time_since_last_rising > 24 * 60 * 60 * 1000:  # 超過1天
        print("重設投幣時間基準，避免溢出問題")
        Coin_IN1_last_rising_time = current_time - 1000
```

3. senko
a. 讓AI改成可以跑mpy
b. 在覆蓋檔案前先備份，並且main.py，可以執行xxxbackup.py
def backup_current_files():
    for file in important_files:
        os.rename(file, file + '.backup')

4. 確認OTA以下更新方式是否正常合理
a. 舊->新
b. 新->新

5. 以下待測試。過一段營運時間後，再確認
a. main.py 不導入Sam20250505以下這段，是否ok? 實測印出記憶體，看起來沒有幫助

    try:
        del ntptime
        del WiFiManager
    except Exception as e:
        print("del error:", e)
        pass
b. github 推送不要有CRLF
c. 滿三天，每天3點，重開機、測試完要還原成正常模式
d. PAYOUT放到>5ms，但要先量測波形
e. 加速Rounds_of_Starting_games的反應速度

6. 需要修改 OTA 程式 senko.py、測試 OTA 是否正常運作。

7. 新增 mqtt-events-spec.md，目前僅涵蓋 events 類封包（qrscan、GiftOut）
未來目標：擴充為完整的 MQTT 封包定義文件，涵蓋所有收（subscribe）和發（publish）的封包格式

8. wifimgr.py get_http_time() 跨年日期計算潛在 bug（AI 檢查發現，低優先）
wifimgr.py 第 249 行，當 12/31 跨年時，month 被賦值為元組 (1, year+1) 而非整數，year 也未更新。
此路徑為 NTP 全部失敗時的備援，且只在 12/31 觸發。
目前多台機器在客人現場長期運行皆正常，暫不修正。
待日後確認後修正：`day, month = 1, (month + 1) if month < 12 else (1, year + 1)` 應改為 else 分支加上 `day, month, year = 1, 1, year + 1`。

9. 大陸扭蛋機投幣器相容性問題（持續觀察）
投10元打一次 pulse，投50元打5次 pulse。
發現連續快速投50元時，小卡會有吃錢現象（pulse 被漏計）。
目前客人實際使用場景不會連續快速投50元，短期內影響不大。
待評估是否需要修正投幣計數邏輯以相容此行為。
