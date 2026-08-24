# code-change list

**2026/8/24_SP3_V0.01a, Thomas**
1. 自 SP2_HWv1 的 SP2_V0.30b 拷貝，建立 SP3 產品線
2. 對應硬體：智付小卡 v2.1（co-layout 板，上件 RGB LED，無 LCD）
3. 本版尚未實作 RGB LED，功能與 SP2_V0.30b 相同
* Based on smartpay2 2025/9/17_SP2_V0.30b, Thomas
---

# 以下為繼承自 branch SP2_HWv1 的歷史紀錄

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

6. Error_Code_of_Machine 故障解除的除法，analogCoinPay_Main.py 中
   (analog_claw_1.Error_Code_of_Machine-24)/100 的 / 應改為 //（整數除法），
   避免型別不一致。影響不大（錯誤碼目前無人查看），暫不修改，
   留待 SP3 V0.30c 與 SP2 一起修正。
