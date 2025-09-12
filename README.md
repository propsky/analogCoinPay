# code-change list

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

2. 加速Rounds_of_Starting_games的反應速度

3. 當IO的last_time太大時，自動清除
# 在10秒檢查迴圈中
if GPI_Claw_Coin_IN1.value() == 1:  # 投幣器待機(高電平)
    current_time = utime.ticks_ms()
    time_since_last_rising = utime.ticks_diff(current_time, Coin_IN1_last_rising_time)
    
    if time_since_last_rising > 24 * 60 * 60 * 1000:  # 超過1天
        print("重設投幣時間基準，避免溢出問題")
        Coin_IN1_last_rising_time = current_time - 1000

4. senko讓AI改成可以跑mpy

5. 確認OTA以下更新方式是否正常合理
a. 舊->新
b. 新->新

6. 過一段營運時間後，再確認
main.py 不導入Sam20250505以下這段，是否ok? 實測印出記憶體，看起來沒有幫助

    try:
        del ntptime
        del WiFiManager
    except Exception as e:
        print("del error:", e)
        pass