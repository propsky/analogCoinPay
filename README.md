## 相關文件
- [狀態燈規格與設計決策](SP3_HWv2.1_RGB狀態燈規格與設計決策_rgb-led-spec.md)
- [push check list](push-check-list.md)

# code-change list

**2026/9/9_SP3_V0.01f, Thomas**  
1. 新增 rgb_led_manager.py（WS2812 單顆狀態燈，取代 LCD）  
a. 以單顆 WS2812（GPIO27，原 LCD_EN 背光腳）顯示系統狀態，共十種燈號  
b. 被動式設計：外部定期呼叫 tick() 推進動畫，模組不自帶 timer / thread  
c. 新增狀態鎖（set_state 的 lock 參數三態），供 OTA／重開機期間鎖住白恆亮不被覆蓋  
d. 全域亮度上限壓低，防手機錄影過曝；燈號規格與設計理由見 rgb-led-spec.md  
2. 刪除 lcd_manager.py：SP3 硬體無 LCD，移除 ST7735 驅動模組  
3. main.py  
a. 移除 LCD：不再匯入 LCDManager、刪除 LCD_EN(GPIO27) 背光初始化與所有 lcd_mgr 繪圖呼叫  
b. 改用 RGB LED：匯入 RGBLEDManager，開機先跑 boot_test()（紅→綠→藍自檢）再進 BOOTING；各階段改以 led_mgr.set_state() 顯示對應燈號  
c. 阻塞點改 50ms 分段並推進燈效：開機延遲、WiFi 連線等待、進主程式倒數（原本 sleep 整秒會讓呼吸/閃爍凍住）  
d. SW1 開機停止：由 sys.exit() 改為 raise KeyboardInterrupt，避免官方 v1.29 把 SystemExit 當 forced-exit 觸發 soft reset 迴圈；兩韌體通用  
4. wifimgr.py（皆向後相容、不依賴 LED 模組）  
a. DHCP 主機名雙韌體分流：新增 _set_hostname()，以 hasattr(network,'hostname') 自動選 API——新韌體用 network.hostname()（active 前設）、舊韌體用 config(dhcp_hostname)（active 後設），確保後台顯示 SmartPay_xxxx  
b. connect() 新增 on_tick / on_ap_mode 兩個回呼參數，預設 None、不傳時行為與原本完全相同  
c. connect() 等待迴圈的 2 秒 sleep 改成 40×50ms 分段，讓外部（LED）可在等待期間推進動畫  
5. analogCoinPay_Main.py  
a. 版本號由 SP3_V0.01a 改為 SP3_V0.01f  
b. 整合 RGB LED：LED_update_callback 依 now_main_state 顯示對應燈號（原為更新 LCD）；safe_reboot() 與 OTA 期間以 set_state(UPDATING_REBOOTING, lock=True) 鎖住白恆亮  
c. three_timer_task 迴圈 sleep 由 200ms 改 50ms 以推進燈效，claw/server 檢查維持約 200ms 節奏  
d. 移除 LCD 顯示相關程式碼（狀態顯示字串、formatted_time 等）  
6. 韌體改用官方 MicroPython v1.29.0，取代原廠商客製 v1.18.9（相容性評估見 SP3_韌體評估_目標v1.29.pdf）  
7. 新增兩份文件檔納入 repo：SP3_HWv2.1_RGB狀態燈規格與設計決策_rgb-led-spec.md（狀態燈規格與設計決策）、SP3_HWv2.1_上機測試檢查清單和測試結果.md（上機驗證清單與結果）  
8. 新增 .gitattributes：強制 *.py / *.json / *.md 以 LF 換行，讓 GitHub 推送只有 LF、不含 CRLF 檔案格式（解決原 to-be-do #5b）  
9. 將 sourceFiles/token.dat、sourceFiles/wifi.dat（機台 wifi 密碼與 token）移出版本控制（git rm --cached）並加入 .gitignore，本機保留、GitHub 之後不再收錄（既有歷史不追溯）  
* Based on smartpay3 2026/8/24_SP3_V0.01a, Thomas
---

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
b. PAYOUT放到>5ms，但要先量測波形  
c. 加速Rounds_of_Starting_games的反應速度

6. 【SP2 與 SP3 都已發現、但尚未修改的共通問題；下一版兩產品線同步修正】  

a. Error_Code_of_Machine 故障解除的除法，analogCoinPay_Main.py 中  
   (analog_claw_1.Error_Code_of_Machine-24)/100 的 / 應改為 //（整數除法），  
   避免型別不一致。影響不大（錯誤碼目前無人查看），暫不修改。  

b. wifimgr.py 的 connect() 有兩個未使用的死參數 timeout=60 與  
   retry_interval=3，迴圈次數(10)與間隔(2秒)都是硬寫。與 LED 無關，暫不修改。  

c. 開機 LED 狀態燈會「短暫倒退」：實機觀察到開機燈號序列為  
    自檢 → 白呼吸(BOOTING) → 紅呼吸(WIFI_CONNECTING) → 黃閃2下(NO_MQTT)  
    → 紅閃1下約2.6秒(NO_WIFI) → 黃閃2下(NO_MQTT) → 綠呼吸(RUNNING) 或 紫閃3下(MACHINE_FAULT)。  
    其中「黃 → 紅 → 黃」是一段倒退。  

    程式邏輯沒錯（LED_update_callback 每 50ms 忠實反映 now_main_state.state），  
    根因是既有架構（SP2 就有）：main.py 先連一次 WiFi 並設燈（連上→黃閃2下），  
    交棒給 analogCoinPay_Main.py 後，其狀態機又從 NONE_WIFI 從頭跑一次、  
    再重連一次 WiFi，那段重連期間 state=NONE_WIFI 就打成紅閃1下。  
    紅閃約 2.6 秒 = 該次重複重連的時間。與 to-be-do #1（不必要的重連 / 想關掉 wifi 模組）同源。  

    兩個缺點：  
    - 視覺倒退：狀態燈由「有網未連MQTT(黃)」退回「沒網(紅)」再前進，  
      現場人員易誤判為網路掉線或當機，破壞狀態燈可信度。  
    - 短暫失真：那 2.6 秒 WiFi 其實是連著的（main.py 已連上），  
      卻顯示紅閃1下=「沒網」，等於顯示了不正確的狀態。  

    影響評估：純外觀 / 短暫，不影響記帳、中斷、MQTT 等核心功能。因牽動與 SP2 共用的  
    狀態機初始化，建議勿在硬體驗證期間更動，留待與 #1 一併處理。  

    三種修法（風險由低到高）：  
    - 方案 A（推薦，治本）：analogCoinPay_Main.py 狀態機初始化時先檢查  
      wifi.isconnected()，若已連線就跳過 NONE_WIFI、直接從 NONE_INTERNET（或  
      NONE_MQTT）起跑，順便省掉那次重複重連。優點：同時解決倒退與 #1 的重連浪費；  
      風險：動到與 SP2 共用的狀態機 init，需回歸測試兩產品線。  
    - 方案 B（治標）：在 LED_update_callback 或狀態燈層加「遲滯」，開機頭幾秒  
      不顯示比先前更差（倒退）的狀態，只允許往前推進。優點：不動狀態機主邏輯；  
      缺點：屬邏輯 hack，需自訂「倒退」判定，且沒解決底層重複重連。  
    - 方案 C：維持現狀。優點：零風險；缺點：倒退與短暫失真仍在。  
      目前（硬體驗證期）先採 C，待 #1 一起做時改 A。

7. 【SP3_0.31a（開發碼 SP3_0.01f）與 SP2_V0.30b 的「共用碼」實際差異——  
   放這裡提醒 SP2 下一版優先補齊此部分，補齊後 SP2_V0.30b 進版為 SP2_V0.31a。  
   兩項皆與硬體差異無關】  

a. wifimgr.py 兩項改動（皆向後相容、不 import/依賴 LED 模組）：  
    (a) 雙韌體 hostname 分流：新增 _set_hostname()，以 hasattr(network,'hostname')  
        自動判別——新韌體(v1.20+)用 network.hostname()、需在 active(True) 之「前」設；  
        舊韌體(1.18.9)用 wifi.config(dhcp_hostname=)、需在 active(True) 之「後」設。  
        兩者 API 與時機相反、皆實測確認。SP2 即使續留舊韌體也可安全對齊（會自動走舊韌體  
        dhcp_hostname 路徑、行為不變）；若日後上 v1.29 則為必要。  
    (b) connect() 新增 on_tick / on_ap_mode 兩個回呼，預設 None、不傳時行為與原本完全  
        相同（僅把等待的 2 秒 sleep 切成 40×50ms 分段）。SP2 的 LCD 不需動畫 tick，此項  
        非必要，僅為讓兩邊 wifimgr 檔案一致可同步。  
    整檔覆蓋前先確認 SP2 的 wifimgr 沒有其他獨立修改（有的話要比對合併，而非直接換）。  

b. SW1 開機停止方式：SP3 已把 main.py 的 sys.exit() 改為 raise KeyboardInterrupt。  
    原因：官方 v1.29 韌體上 sys.exit()/SystemExit 會被當 forced-exit 觸發 soft reset、  
    造成重開迴圈，停不進 REPL；改用一般例外 KeyboardInterrupt 則兩韌體  
    (v1.29 與 1.18.9 皆實測) 都會乾淨掉到 REPL，且此寫法兩韌體通用、不需分支。  
    SP2 為減少程式碼分歧可直接採用（舊韌體 sys.exit() 也能用，此寫法兩韌體通用、行為不變）。  

c. 新增 .gitattributes（強制 *.py / *.json / *.md 為 LF）：SP2_V0.30b 進版到 SP2_0.31a 時也要一併做，確保 GitHub 上只有 LF、不含 CRLF 檔案格式。

d. 將 token.dat / wifi.dat 移出版本控制（git rm --cached ＋ 加 .gitignore）：SP2_V0.30b 也把機台 wifi 密碼與 token 只留本機、不進 repo。

8. AP 設定模式（清空 wifi.dat 觸發）兩個問題，AP 模式現行未使用、暫不修：  

a. 狀態燈凍住：wifimgr.py 的 start_ap_web() 進入 while True 卡在 socket.accept()，  
   期間沒有呼叫 led_mgr.tick()，WIFI_CONFIG 的水藍呼吸就凍在某一幀（低亮度水藍看似微弱藍）。  
   這是被動式 tick 設計漏插的阻塞點（UDP 設定模式無此問題，因其等待迴圈有 tick）。  
   修法：accept() 前用 settimeout 改非阻塞輪詢，在等待迴圈內呼叫 tick()，  
   比照 UDP_Load_Wifi 與 wifimgr.connect() 的 50ms 分段 tick 作法。  

b. 設定網頁只顯示 HTML 原始碼、沒有輸入欄：handle_web_requests() 回傳的 HTML 字串  
   每行含縮排，連 HTTP 標頭列（HTTP/1.1 200 OK、Content-Type 等）都被縮排，  
   導致 HTTP 回應格式不合法，瀏覽器當純文字顯示。此為 SP2 就沿用的舊寫法（老闆改過），  
   非 SP3 改動造成。修法：把標頭與空行頂格、body 才是 HTML，或改用不含縮排的字串。  

註：a 屬 SP3 LED 相關、b 屬 SP2 就有的既有問題；若日後要重啟 AP 設定模式再一併處理。
