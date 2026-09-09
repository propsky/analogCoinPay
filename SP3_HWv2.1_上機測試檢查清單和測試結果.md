# SP3_HWv2.1 上機測試檢查清單和測試結果

> 最後更新：2026-09-09 21:15
> 產出：2026-09-06 00:12　作者參考用；保留於根目錄供約半年參考，未來同類檔案變多再做資料夾分類（不隨發布刪除）。
> 對象：LED stage2 + hostname 分流 + SW1 三包改動，於真實娃娃機上驗證。
> 用法：每項測完自己打勾；發現異常記在該項下方。

---

## 0. 已完成（bench 已驗，可略）

- [x] hostname 新韌體 v1.29：手機顯示 `SmartPay_xxxx`、log 印 `[新韌體 network.hostname]`
- [x] hostname 舊韌體 1.18.9：手機顯示 `SmartPay_xxxx`、log 印 `[舊韌體 dhcp_hostname]`
- [x] SW1 停止：兩韌體皆 `raise KeyboardInterrupt` 乾淨掉 REPL，無 soft reset 迴圈
- [x] MAC 末三碼 = 主機名尾碼 = 手機顯示，三邊一致
- [x] 狀態機開機一路到 STANDBY_MQTT
- [x] RGB 重複 initialize() guard 生效（印「已初始化，略過」）

---

## 1. LED 十種燈號目視驗證（核心新功能）

逐一確認顏色 + 節奏正確：

- [x] **BOOT_TEST**　上電自檢：紅→綠→藍，各約 0.5 秒
- [x] **BOOTING**　開機中：白，呼吸（約 2 秒一循環）
- [x] **WIFI_CONNECTING**　連線嘗試中：紅，呼吸
- [x] **WIFI_CONFIG（UDP 設定模式）**　水藍，呼吸（觸發：按 SW4 進 UDP）
- [ ] **WIFI_CONFIG（AP 設定模式）**　水藍，呼吸（觸發：清空 wifi.dat）
      ⚠ 實測**卡在藍色微亮、呼吸凍住**；且手機開設定網頁只顯示 HTML 原始碼、無輸入欄。
      根因見下方「AP 模式兩個問題」；AP 模式現行未使用，暫不影響營運。
- [x] **NO_WIFI**　連不上 Wi-Fi：紅，閃 1 下（故意不開目標 wifi AP）
- [x] **NO_MQTT**　有網無 MQTT：黃，閃 2 下（有連上 wifi AP，但故意擋外網）
- [x] **MACHINE_FAULT**　娃娃機故障：紫，閃 3 下（觸發故障偵測）
- [x] **RUNNING**　正常運行：綠，呼吸（連上 MQTT 且無故障時）
- [x] **UPDATING_REBOOTING**　OTA 更新 / 重開機：**白，恆亮**（三種觸發皆已測白恆亮）：
      1. 收到 MQTT `<macid>/<token>/fota` 指令 → 寫 otalist.dat + safe_reboot()，重開後 main.py 跑 OTA
      2. 開機時檔案系統有 `otalist.dat` → main.py 跑 OTA（用 MQTT OTA 指令把不存在的 .py 寫進 otalist.dat 來測）
      3. 定期重開 safe_reboot()：debug 版滿3小時整點後30分（:722-726，測時解除註解；正式版是滿3天早上3點）
      根因與修正（已生效）：three_timer_task 跑在獨立 thread，原本 safe_reboot 期間 thread 會把白燈覆蓋回
      營運狀態（沒接娃娃機→MACHINE_FAULT 紫閃）。已在 set_state 加 lock，safe_reboot 與 main.py OTA 用
      lock=True 上鎖，白燈固定到 reset。實測三種觸發皆全程白恆亮、不再紫閃。（鎖規格見 rgb-led-spec.md 第八節）
- [x] **STOPPED**　SW1 停止：紅，恆亮

檢查點：
- [x] 呼吸/閃爍**不會凍住**（開機延遲、UDP 等連線、wifi 重試、倒數皆已分段 tick）
      例外：**AP 模式會凍住**（start_ap_web 阻塞未 tick），見下。
- [x] 狀態切換乾淨，不殘留前一色
- [x] 亮度不過曝（手機錄影可辨識顏色）

### AP 模式兩個問題（實測發現，非本次 LED 新功能的核心，AP 模式現未使用）
1. **LED 凍住（看起來藍色微亮、不是水藍）**：`wifimgr.start_ap_web()` 進 `while True` 卡在 `socket.accept()`，
   期間沒呼叫 `led_mgr.tick()`，呼吸凍在**第 0 幀**——而 breathe 第 0 幀剛好是最低亮度（`_BREATHE_MIN=0.08`）。
   水藍 (0,180,255) 在「亮度25 × 0.08」換算後約 (0,1,2)：綠被整數截成 1（幾乎看不見）、藍是 2（微亮），
   所以只剩微弱藍、綠像沒亮。正常呼吸到峰值 (0,17,25) 才會是明顯水藍。
   對照：UDP 模式連線前沒事，因 `UDP_Load_Wifi` 等待迴圈有 `tick()`。
2. **設定網頁顯示原始碼、無輸入欄**：`handle_web_requests()` 的 HTML 字串每行含縮排，
   連 HTTP 標頭列（`HTTP/1.1 200 OK` 等）都被縮排 → HTTP 回應格式不合法 → 瀏覽器當純文字顯示。
   此為 SP2 就沿用的舊寫法（老闆改過），非本次改動造成。

### UDP 模式補充觀察（已知；依使用者指示只記錄、不改程式）
UDP 設定模式：連上 Sam AP **之前**是正常水藍呼吸；**連上之後、收到 UDP message 之前**，水藍會凍住
（停在當下呼吸亮度、不再起伏）。同類根因：`UDP_Load_Wifi` 連上後進 `while True` 的 `udp_socket.recvfrom()`
阻塞、期間沒 `tick()`。此模式僅設定時短暫使用，不影響營運。

---

## 2. 中斷完整性（最高風險 — LED write 會短暫關 IRQ）

在**燈效持續刷新**（呼吸或閃爍進行中）的同時投幣/出獎，貼 log 對照實測脈波寬度。
判讀方法：看每筆 `Low Pulse寬度(ms)`，落在設定值 ±10ms 即通過（投幣器脈波已調查為市面最小/最大值）。
註：`ticks_ms()` 解析度 1ms，數字本就會 ±1ms 量化跳動；LED `neopixel.write()` 關 IRQ 僅 ~30µs，理論上影響 <<1ms，本測即為實測證實。

> 訊號對照（實機確認）：Coin_IN1/IN2＝投幣（Coinplaytimes）；**PAYOUT 腳＝票證卡機刷卡成功**（Epayplaytimes，非出獎）；**電眼 Eyes_IROUT＝偵測出獎**（GiftOuttimes）。

### 大量測試 log 逐筆統計（2026-09-08，LED 動畫運行中）

| 訊號 | ✅通過 | ❌失敗 | 實測 Low 寬度 | 設定/門檻 |
|---|---|---|---|---|
| Coin_IN1（投幣） | 32 | 0 | 20ms×26 / 21ms×6 → 20~21 | ~20ms |
| Coin_IN2（投幣） | 35 | 0 | 100 / 101ms → 100~101 | ~100ms |
| PAYOUT（刷卡成功） | 40 | 0 | 150×37 / 149×1 / 151×2 → 149~151 | ~150ms |
| 出獎（電眼 IROUT） | 12 | 4 | 通過者 294~626 | Low 10~800、Hi≥1000 |

投幣＋刷卡 107 筆全過、寬度 ±1ms。記入：投幣→Coinplaytimes、刷卡→Epayplaytimes、出獎→GiftOuttimes。

> 註：本表（09-08）投幣器設定為 **IN1≈20ms、IN2≈100ms**；之後的離線/reset 測試已把兩軌**對調成 IN1=100ms、IN2=20ms**（見下方網路狀態表）。故兩表的 IN1/IN2 設定值相反，非筆誤。

**電眼 4 筆失敗明細：**

| # | Hi(ms) | Low(ms) | 判定原因 |
|---|---|---|---|
| 1 | 0 | 369213 | 開機首發 stale-reference：Low 遠超 800、Hi<1000 |
| 2 | -369213 | 369225 | 首發後緊接第二個 rising、中間無 falling → Hi 負 |
| 3 | -589 | 610 | 出獎後第二個 rising、無 falling（Low 其實在範圍內，但 Hi 負被擋）|
| 4 | -367 | 387 | 同 #3 |

→ 4 筆皆為電眼訊號極短彈跳造成的「多 rising / 少 falling」未配對 rising，被負-Hi 正確擋掉、不重複計獎。

**邊緣配對（有無掉一邊）：**

| 訊號 | 配對結果 |
|---|---|
| Coin_IN1/IN2、PAYOUT | 全成對、**零掉邊**（含 2 處中斷交錯：Coin_IN2 中插 PAYOUT、PAYOUT 中插 Coin_IN1，四邊緣皆完整、GPIO_Send 次數正確）|
| 電眼 IROUT | 4 筆未配對 rising（如上表），已過濾、不影響計數 |

- [x] **無漏抓（vs 實際投入數）**：兩次定量投幣皆「偵測數＝實際投入數」完全吻合——
      離線 NONE_WIFI 下 6枚×3批＝各 18 筆（IN1 18 / IN2 18，全對）；有WiFi無外網下 reset 後各投 30 枚（IN1 30 / IN2 30，全對）。
      全部脈波乾淨有效、零漏零重；reset 瞬間 Coin_IN2 與 PAYOUT 各一筆 `Low:0ms` 上電瞬變被寬度過濾器正確擋掉、不誤計（不吃錢）。

> 已知非問題（2026-09-08 實測）：**接娃娃機的小卡**每次 soft reboot，init 階段會出現一筆
> `Coin_IN2 Low Pulse=0ms` 的開機瞬變（未接娃娃機的小卡不會）。屬 Coin_IN2 線上電瞬變、非投幣、
> 且發生在 LED thread 啟動前（與 LED 無關）。已被寬度過濾器（Low 需 5~300ms）正確擋掉、不誤記。

### 投幣脈波量測誤差 vs 網路狀態（未來「吃錢」排查基準）

投幣器實測 Low 寬度會因主迴圈忙碌程度而抖動——**網路重連越忙、軟排程 IRQ 延遲越大、量測值抖越多**。
下表以「設定值」分軌（不綁 IN1/IN2 名稱，避免與上表對調混淆）：

| 狀態 | 燈號 | 設 100ms 軌實測 | 設 20ms 軌實測 | 最大誤差 |
|---|---|---|---|---|
| MQTT OK（正常）| 綠呼吸 | 100~101 | 20~21 | ±1ms |
| NONE_WIFI（斷網重連）| 紅閃 | 100 | 20~23 | +3ms |
| **NONE_MQTT（有WiFi無外網）** | **黃閃** | **98~110** | **12~30** | **−8 ~ +10ms** |

- **最抖的是 NONE_MQTT（黃閃）**：MQTT socket 連線阻塞（每輪 -202 失敗）最吃 CPU，把軟排程的 IRQ 拖最久。
- **PAYOUT（刷卡，設 150ms）相對穩**：各狀態都在 149~151、黃閃下也沒明顯放大——脈波較寬，同樣的絕對延遲換算成相對誤差就小。
- 但**接受窗是 Low 5~300ms**，最壞值（12ms / 110ms）離上下限都還很遠，
  **真實投幣在任何網路狀態都不會因抖動被擋 → 網路狀態不造成吃錢**。唯一被擋的 `Low:0ms` 是 reset/上電瞬變、非投幣，本該擋。
- **未來遇「投錢不啟動遊戲」先看該筆 log 的 `Low Pulse寬度`**：
  落在 5~300ms 卻沒 `啟動娃娃機遊戲` ＝ 計數/GPIO 端問題；落在窗外（0ms 或 >300ms）＝ 硬體脈波/瞬變，非韌體誤擋。

---

## 3. 記帳 / 故障 / 電源控制

- [x] IN / EPAY / OUT 數值與實際動作一致：投幣→IN、刷卡→EPAY、出獎→OUT，多次逐筆吻合（各18/各30 投幣全對、出獎 5 及 10 次全對、刷卡逐筆對上）。
      FPLAY（免費玩）過去已測過、功能正常；但目前在外運行的歷代小卡都沒使用此功能，故本次不再測。未來業務上若啟用 FPLAY，會再補測。
- [x] meter.json 正確存檔、重開機後數值保留：reset 後開機 log 印 `成功從 meter.json 載入資料: {EPAY:86, IN:282, OUT:37, FPLAY:0}`；離線期間累積的投幣數撐過 reset 不歸零。
- [x] 故障觸發 → LED 變 MACHINE_FAULT，且卡機/投幣器電源依邏輯關閉
- [x] 故障解除 → LED 回 RUNNING，電源恢復

> 實測（2026-09-09，log 佐證）：
> - 觸發：`Fault_Detect改變成:1`、status `00→24`，LED **綠呼吸→紫閃3下**；故障持續約 30 秒內**完全無任何投幣/刷卡中斷**（電源確實切斷，手測外部也無法刷卡/投幣）。
> - 解除：`Fault_Detect改變成:0`、status `24→00`，刷卡/Coin_IN1/Coin_IN2 三訊號立即恢復啟動（Coin 157→159、Epay 55→56）。
> - **不吃錢佐證**：電源恢復瞬間 Coin_IN2 出現一筆 `Low:0ms` 上電瞬變，被寬度過濾器正確擋掉、未誤記投幣。

---

## 4. OTA 流程（README to-be-do #4）

- [ ] 舊版 → 新版 OTA：更新成功、UPDATING_REBOOTING 白恆亮、更新後 reboot
- [ ] 新版 → 新版 OTA：無多餘更新時正確略過
- [ ] senko 抓的 branch 是 `SP3_HWv2.1`、working_dir `releaseFiles/latestVersion`

---

## 5. 長時間穩定度

- [x] 連續運行 ≥ 數小時無 crash、無 reset 迴圈：**~3AM 自動重開後連續跑 12 小時**（2026-09-09），uptime 平順爬升、無 crash、無重開迴圈
- [x] gc.mem_free 穩定，無持續下滑（記憶體洩漏）：全程穩在 ~82600（±80），零下滑
- [x] WDT 正常餵狗，不會誤觸重開：12 小時間 WDT 規律餵狗、無誤觸重開
- [x] 滿 3 天早上 3 點自動重開機邏輯：uptime 由 2.8 天跨過 3 天 → **~3AM 觸發重開** → 現重置為 ~12h。
      （依 uptime 重置＋MQTT 時間戳 842281966≈2026-09-09 15:07 推算重開在 ~03:00，吻合 `days>=3 且 hour==3`；
      重開瞬間 `準備重開機...` 訊息未直接錄到，但時間精準對上、非隨機 WDT/斷電可解釋）

---

## 6. 收尾 / 發布前

> 本次為 **OTA 測試發布 SP3_V0.01f**（供測「SP3_V0.01a → SP3_V0.01f」OTA）；待 OTA 驗證通過後定版 **SP3_0.31a**，屆時版號相關項目需再跑一次。

- [ ] 程式版本字串（analogCoinPay_Main.py 第 1 行）定案：目前 SP3_V0.01f（OTA 測試碼），最終 SP3_0.31a 待 OTA 測完定案
- [x] README / CLAUDE.md 版本號與硬體描述同步（GPIO27→WS2812、移除 LCD）：已同步（版號暫記 SP3_V0.01f、最終 SP3_0.31a）
- [x] sourceFiles/ → releaseFiles/latestVersion/ 覆蓋：兩邊程式碼一致（排除 token.dat/wifi.dat、已刪 lcd_manager、已加 rgb_led_manager）
- [x] releaseFiles/ 建立版本 zip：SP3_V0.01f.zip
- [x] README code-change list 補這版紀錄：SP3_V0.01f 條目（含檔案 rename、.gitattributes、token/wifi 移出追蹤）
- [ ] 三包 commit（message 先給 Thomas 確認）：message 已確認，push 進行中
- 本檔保留於根目錄供約半年參考，不隨發布刪除；未來同類檔案變多再做資料夾分類。
