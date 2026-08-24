# code-change list

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
**2025/9/4_SP2_V0.20a, Thomas**
1. main.py 大修改
a. 整合開心小卡B1，和Branch main中Sam寫的"修正thomas版的main" committed on May 6。比對功能，以及導入較省記憶體的方式
b. OTA更新機制修正刪除檔案和重開機
c. 整理Log和註解
b. from utime import sleep改成import utime，一步一步統一用法
2. wifimgr.py 小修改
a. import time改成import utime，一步一步統一用法
b. DHCP_NAME = "SmartPay_" + MAC後六碼
3. 修改to-be-do list
* Based on smartpay2 8/29_SP2_V0.0829sb, Thomas
---
**2025/8/29_SP2_V0.0829sb, Thomas**
1. pulse_time的時間寬度改用utime.ticks_diff(time2, time1)，可以避免utime.ticks_ms()溢位後的回繞問題
2. pulse_time的名稱改成pulse_ms、Eyes_Enable_time改成Eyes_Enable_interval_ms，要和rising_time(utime.ticks_ms())作區別。
3. 開機秒數:utime.ticks_ms() / 1000，改成使用get_uptime_str()函式，顯示成開機時間:d日 h時 m分 s.ss秒
4. 因為新版analogCoinPay_Main.py程式太大執行不了，所以刪掉各種註解、重複部分用變數減少字數
5. 修改to-be-do list
* Based on smartpay2 8/13_SP2_V0.0813sd, Thomas
---
**2025/8/13_SP2_V0.0813sd, Thomas**
1. 修改電眼上數的條件：物品要離開電眼1秒鐘以上，接著物品遮住0.01~0.8秒，以上兩個都成立才上數
2. 修改電眼中斷時的Log敘述
3. 當通用電眼的PIN define反接時，IROUT會反向；所以此版開通 當判定為通用電眼時，常態Hi或常態Low，都能出獎+1
4. 修改to-be-do list和push check list 
* Based on smartpay2 7/31_SP2_V0.0731sa, Thomas
---
**2025/7/31_SP2_V0.0731sa, Thomas**
1. 新增push check list(./push-check-list.md)
2. Eyes_IRDIS新增進中斷，紀錄正緣和負緣的時間點，Is_FEILOLI_eyes改到此中斷進行判斷和修改
3. Eyes_IROUT中斷後，不判斷Eyes_IRDIS、不修改Is_FEILOLI_eyes；飛絡力電眼的部分，新增判斷Eyes_Enable_time(IRDIS正緣->IROUT負緣)時間要大於500ms
4. 為了防只同樣的準位下，出現非預期的重複中斷。PAYOUT、Coin_IN1、Coin_IN2新增last_value，各自中斷時，會先判斷新值和舊值有沒有改變，若有才會做後續中斷處理。
5. 2和4的狀態再開機時會先讀取和修改，並且列印出log。
6. 刪掉多餘的空白和註解掉用不到的程式碼。
* Based on smartpay2 7/15_SP2_V0.0610sd, Thomas整理Sam修改
---
**2025/7/15_SP2_V0.0610sd, Thomas整理Sam修改**
1. 補上Sam的修改紀錄
a. Sam上傳了ntptime.py
b. Sam更新了senko.py
* Based on smartpay2 2025/6/10_SP2_V0.0610sb, Thomas
---
**2025/6/10_SP2_V0.0610sb, Thomas**
1. MQTT收到OTA指令時，在重開機以前會先關掉卡機電源和刷卡功能，以及關掉投幣器電源
* Based on smartpay2 2025/6/10_SP2_V0.0610sa, Thomas
---
**2025/6/10_SP2_V0.0610sa, Thomas**
1. wifi斷線時，不影響投幣器、卡機、電眼的相關功能，並且仍能定期清除WDT
2. 新增meter功能
3. 可以接受MQTT的epays、freeplays的啟動指令
4. 簡化MQTT publish重複的程式碼
5. 調整如果MQTT傳送失敗，就把狀態打回Wi-Fi斷線
6. 新增娃娃機故障偵測與對應處理GPIO設定的副程式
7. LCD導入Sui的新LCD模組py檔
8. 判斷電眼enable訊號，若曾經有enable就是飛絡力電眼，出獎判斷Low寬度；
	否則就是通用型電眼，出獎判斷Hi寬度
9. 為了等待中華4G用的TPLINK基地台開機，main.py連wifi以前會delay 60秒
	=> 此為短期解法會造成開機很久，應當找時間修正成長期解法
10. main.py會關掉卡機電源、投幣器電源、EPAY_EN
* Based on smartpay2 2025/5/5_SP2_V0.0505a, Thomas
---
**2025/5/5_SP2_V0.0505a, Thomas**
1. 完成投幣器、卡機傳給娃娃機的投幣訊號串接
* Based on smartpay2 2025/3/5_SP2_V0.01a, Thomas
---
**2025/3/5_SP2_V0.01a, Thomas**
1. 以智付小卡硬體V1.0開發，刪除smartpay1 SPHP_V1.00c的FEILOLI UART
2. MQTT暫時可以上傳了，但還有許多未修改確認部分，可能有BUG
* Based on smartpay1 2025/3/5_SPHP_V1.00c, Thomas
---

# to-be-do list

1. 修補小卡的重連機制，不嘗試連線時，想要完全關掉wifi模組
=> 這樣也能解決main執行時都要延遲一分鐘才能繼續開機

2. 當IO的last_time太大時，自動清除
# 在10秒檢查迴圈中
if GPI_Claw_Coin_IN1.value() == 1:  # 投幣器待機(高電平)
    current_time = utime.ticks_ms()
    time_since_last_rising = utime.ticks_diff(current_time, Coin_IN1_last_rising_time)
    
    if time_since_last_rising > 24 * 60 * 60 * 1000:  # 超過1天
        print("重設投幣時間基準，避免溢出問題")
        Coin_IN1_last_rising_time = current_time - 1000

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
