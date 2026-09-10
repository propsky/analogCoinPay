# 狀態燈設計決策

> 最後更新：2026-09-10 19:29

SP3 硬體移除 LCD，改用單顆 WS2812 狀態燈（`rgb_led_manager.py`，GPIO27）只顯示「系統狀態」；帳目資訊改為只從 MQTT 後台查詢。本文件記錄該模組的規格與設計理由（`.py` 內只保留精簡註解，理由性說明集中於本文件）。

## 一、判讀管道與燈號編碼原則

這顆燈的最終判讀管道是「手機影片」：店員發現機台沒資料 → LINE 客服 → 客服請店員錄影燈號回傳 → 客服判讀。由此推導出的原則（**實作時請勿更動節奏參數**）：

- **以「閃幾下」為主要編碼、顏色為輔助**。三個最常見故障用 1 / 2 / 3 下區分，即使顏色在影片中過曝成白色，數閃爍次數仍能判讀。
- **每個燈號需在 2 秒內辨識完一輪**。
- **呼吸類永遠有光（最低約 8%）、閃爍類會全暗**。這是刻意的：兩類在影片裡才能一眼分辨（呼吸＝持續有光、閃爍＝會熄）。

## 二、十種燈號規格

| 狀態常數 | 顏色 | 節奏 |
|---|---|---|
| `BOOT_TEST` | 紅→綠→藍 | 上電自檢，各 500ms（共 1500ms），由 `boot_test()` 阻塞執行 |
| `BOOTING` | 白 | 呼吸，週期 2000ms |
| `WIFI_CONFIG` | 水藍 | 呼吸，週期 1000ms |
| `WIFI_CONNECTING` | 紅 | 呼吸，週期 2000ms |
| `NO_WIFI` | 紅 | 閃 1 下（亮150+暗150，停1000） |
| `NO_MQTT` | 黃 | 閃 2 下 |
| `MACHINE_FAULT` | 紫 | 閃 3 下 |
| `RUNNING` | 綠 | 呼吸，週期 2000ms |
| `UPDATING_REBOOTING` | 白 | 恆亮（OTA 更新 / 重開機共用；期間阻塞不 tick 無法閃動，故用恆亮） |
| `STOPPED` | 紅 | 恆亮 |

> `WIFI_CONNECTING`（紅呼吸）與 `NO_WIFI`（紅閃 1 下）是**不同**狀態，不可合併：前者＝還在重試、尚未有結論；後者＝10 次都失敗、確定連不上。影片裡從「不熄滅」變成「會全暗」，對客服判讀有價值。

> **同色靠「節奏」區分，判讀時先看動態再看顏色：**
> - **白有兩種**：`UPDATING_REBOOTING`（白**恆亮**）＝OTA 更新／重開機、忙碌別斷電；`BOOTING`（白**呼吸**）＝開機中。
> - **紅有三種**：`WIFI_CONNECTING`（紅**呼吸**）＝連線中；`NO_WIFI`（紅**閃 1 下**）＝連不上；`STOPPED`（紅**恆亮**）＝SW1 停止。

### 實際顏色值（RGB 全值，亮度上限與 `_scale` 換算見程式）
紅 `(255,0,0)`、綠 `(0,255,0)`、藍 `(0,0,255)`（僅自檢 sweep 用）、白 `(255,255,255)`、黃 `(255,255,0)`、**水藍 `(0,180,255)`**、**紫 `(160,0,255)`**。

顏色沿革（2026-09）：
- **水藍原為青 `(0,255,255)`**：青較不易辨識，且與（舊）`UPDATING` 的藍近似，改為偏藍的水藍。
- **紫原為洋紅 magenta `(255,0,255)`**：洋紅（偏粉紫紅）辨識度低，改為真正的紫。
- 水藍（綠+藍）與紫（紅+藍）一綠一紅，彼此及與其他色都分得開。

## 三、被動式設計：為何不用 timer / thread

模組**沒有自己的時間來源**，不建立 `machine.Timer` 或 `_thread`。燈效是被動的——外部呼叫 `tick()` 時才用 `utime.ticks_ms()` 推算目前該顯示哪一幀（相位靠時間算、不靠被呼叫幾次，並用 `ticks_diff` 處理溢位）。

理由：**1.18.9 上實測發現，不論硬體或軟體 timer，其 callback 執行期間外部中斷都無法即時處理**（Timer callback 與 GPIO soft-irq 共用排程器），因此本專案早已改用 `_thread` 迴圈（three-task）承載週期性工作。LED 的 `tick()` 很短（算一幀 + 最多一次約 30µs 的 WS2812 寫入），放進「會頻繁 sleep 的既有迴圈」最符合這個已驗證、對投幣/電眼中斷友善的模式，**不需要另外動用任何 Timer**。

另外，`_output()` 會在顏色與上次相同時略過寫入（WS2812 寫入期間關中斷約 30µs），避免恆亮/停頓/全暗狀態下的無謂開銷干擾投幣脈波偵測。

## 四、四個必須插 `tick()` 的阻塞點

因為模組被動，任何超過約 1 秒的阻塞等待都必須改成 50ms 分段、每段呼叫一次 `tick()`，否則動畫會凍在第 0 幀（＝呼吸的最低亮度；呼吸看起來像微弱恆亮、閃爍看起來像恆亮）。**必須處理的有四處**（另有兩處刻意不處理，見本節末）：

1. **開機延遲**（`main.py` 依 `config.json` 的 `boot_delay_sec`；多數機台無此檔、走程式預設 3 秒，少數特殊機台放 config 檔設 60 秒）
2. **`UDP_Load_Wifi()` 等待 WiFi 連線的迴圈**（`main.py`）
3. **`wifi_manager.connect()` 的重試迴圈**（`wifimgr.py`，實際為 10 次 × 2 秒 = 20 秒，經 `on_tick` 回呼推進）

   > 註：`connect()` 簽章上的 `timeout=60` 與 `retry_interval=3` 兩個參數在函式主體中皆未被使用（迴圈次數與間隔都是硬寫的）。屬既有的無關瑕疵，依「不順手修無關缺陷」原則本次不動，記錄於此以免日後重複追查。
4. **進主程式前的倒數 3 秒**（`main.py`）

> **另外兩處刻意不處理**（皆屬設定模式、不需靠燈判讀）：AP 模式（`start_ap_web()` 的 `socket.accept` 阻塞）與 UDP 模式**連上 AP 之後**的 `udp_socket.recvfrom` 阻塞，皆**刻意不處理**、也不為此改 socket timeout。正常出貨流程是預先放好 `wifi.dat`、不走這些設定模式；真的用到的是 FAE 或維修工程師，不需要靠燈號判斷。（UDP 模式連上 AP 之前仍會呼吸，因等待連線的迴圈有 `tick()`；連上後等 UDP 訊息才凍住。）
>
> **凍住時的視覺（預期現象、非設定錯誤）：** 呼吸會凍在**第 0 幀＝最低亮度**（`_BREATHE_MIN=0.08`）。低亮度下較小的顏色通道會被整數截斷到「看不見」——例如水藍 `(0,180,255)` 在「亮度25 × 0.08」約為 `(0,1,2)`，綠(1)幾乎不亮、只剩微弱藍，看起來就不像水藍。正常呼吸到峰值 `(0,17,25)` 才是明顯水藍。

## 五、解耦回呼：`on_tick` / `on_ap_mode`

`wifimgr.py` **不 import、也不認識 LED 模組**；它只透過回呼在特定時機通知外部，由 `main.py` 決定要對應哪個燈。

- **命名規則**：`on_<事件>`（snake_case），預設 `None`（不傳時行為與原本完全相同）。
- `on_tick`：重試等待期間每 50ms 呼叫一次（週期性，用來推進 LED 動畫）。
- `on_ap_mode`：即將進入 AP 設定模式時呼叫一次（事件性）。它同時解決一個實際漏洞——原本 `main.py` 無從得知 `connect()` 內部走了 AP 模式分支；有無這個回呼與「燈會不會凍住」是兩回事。

`main.py` 的用法：先無條件設 `WIFI_CONNECTING`，再把 `on_ap_mode` 對應到 `set_state(WIFI_CONFIG)`；連線分支的判斷只留在 `wifimgr` 一處，不在 `main.py` 重複。

## 六、開機各階段 → 對應燈號（`main.py`）

| 開機位置 | 燈號 |
|---|---|
| 初始化完成後 | `boot_test()` → `BOOTING` |
| SW1 按下（`raise KeyboardInterrupt` 前） | `STOPPED` |
| SW4 或 FEILOLI 拉低 → `UDP_Load_Wifi()` | `WIFI_CONFIG` |
| 開機延遲期間 | 維持 `BOOTING` |
| 呼叫 `connect()` 之前 | `WIFI_CONNECTING` |
| 連線中判定要進 AP 模式（`on_ap_mode`） | `WIFI_CONFIG` |
| WiFi 連線成功 | `NO_MQTT` |
| 重試 10 次皆失敗 | `NO_WIFI` |
| 執行 OTA | `UPDATING_REBOOTING` |
| 倒數 3 秒進主程式 | 維持前一狀態 |

營運後由 `analogCoinPay_Main.py` 每 tick 依「狀態機狀態 + 故障碼」推導：`NO_WIFI` → `NO_MQTT` → `MACHINE_FAULT` → `RUNNING`（優先權順序不可更動）。`safe_reboot()`（OTA、定期重開機、MQTT fota）期間顯示 `UPDATING_REBOOTING`。

## 七、日後若考慮改用 timer

這條「不用 timer」的禁令不是永久的，但要跨過去必須先通過以下驗證，不可只憑「桌上測起來正常」：

1. 接實體娃娃機，連續投幣 200 次以上，確認計數零漏記
2. 同時觸發電眼與出獎訊號，確認中斷不漏
3. 連續運行 24 小時，確認長時間下沒有累積性漏失

過去的問題正是「桌上測正常、上機才掉錢」，所以驗證必須在真實機台上、用足夠的樣本數進行。這樣它從「不准動」變成「要動請先證明」，比較經得起時間。

## 八、狀態鎖（`set_state` 的 `lock` 參數）

### 為什麼需要鎖
`three_timer_task` 跑在**獨立執行緒**（`analogCoinPay_Main.py` 的 `_thread.start_new_thread`），每 ~50ms 呼叫 `LED_update_callback` 依營運狀態設燈。`safe_reboot()` 想顯示白恆亮（`UPDATING_REBOOTING`）時，這條 thread 不會被主程式的 `utime.sleep()` 擋住，會繼續把白燈覆蓋回營運狀態（例如沒接娃娃機時的 `MACHINE_FAULT` 紫閃）。實測：safe_reboot 期間全程紫閃、看不到白燈。故需要一個鎖，讓白燈設定後不被 thread 蓋掉，直到 `reset`。

### `lock` 三態語意
`set_state(state, lock=None)`：

- **`lock=None`（不餵，預設）**：一般模式。若目前**已鎖**則忽略此次呼叫；未鎖則正常換狀態（同狀態不重設相位）。
- **`lock=True`**：強制執行並**上鎖**。上鎖後，除了 `lock=False`，任何呼叫（含再一次 `lock=True`）都動不了它。
- **`lock=False`**：強制執行並**解鎖**。

> 設計取捨：已鎖時**連 `lock=True` 也擋掉**，只有明確 `lock=False` 能動它。理由是讓「鎖」成為真正的互斥保護——要接手就得明確解鎖，避免關鍵狀態（重開/OTA 白燈）被別處默默覆蓋。代價是想換另一個鎖定狀態要「先解鎖再上鎖」兩步，但這需求極少、且逼呼叫者表明意圖，較安全。

### 呼叫 → 行為對照表
| 目前 | 呼叫 | 行為 |
|---|---|---|
| 未鎖 | `set_state(X)` | 正常換（同狀態不重畫）|
| 未鎖 | `set_state(X, lock=True)` | 換 X ＋上鎖 |
| 未鎖 | `set_state(X, lock=False)` | 換 X（解鎖，本就未鎖）|
| **已鎖** | `set_state(X)` | **忽略** |
| **已鎖** | `set_state(X, lock=True)` | **忽略** |
| **已鎖** | `set_state(X, lock=False)` | 換 X ＋解鎖 |

### 目前使用處
- `safe_reboot()`（`analogCoinPay_Main.py`）：`set_state(UPDATING_REBOOTING, lock=True)` — 主要用途，thread 存活期間靠它固定白燈。
- `main.py` OTA 區塊：`set_state(UPDATING_REBOOTING, lock=True)` — 此處尚無 LED thread、本不會被蓋，加 `lock=True` 純為語意一致。
- `lock=False`（解鎖）目前**無呼叫處**，先做起來讓 API 對稱、不變成單向鎖死。
- 鐵則：`lock=True` 只能用在「後面馬上 `reset`」的狀態；對正常狀態上鎖會讓燈鎖死到 reset。

## 九、2026-09-08 實作後測試結果

（LED 目視驗證結果為 2026-09-08 實測，同時記於上機測試檔 SP3_HWv2.1_上機測試檢查清單和測試結果.md 第 1 節；此處一併永久保存。）

### LED 十種燈號目視驗證
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
      lock=True 上鎖，白燈固定到 reset。實測三種觸發皆全程白恆亮、不再紫閃。（鎖規格見上方第八節）
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
   所以只剩微弱藍、綠像沒亮。正常呼吸到峰值 (0,17,25) 才會是明顯水藍。（原理見第四節）
   對照：UDP 模式連線前沒事，因 `UDP_Load_Wifi` 等待迴圈有 `tick()`。
2. **設定網頁顯示原始碼、無輸入欄**：`handle_web_requests()` 的 HTML 字串每行含縮排，
   連 HTTP 標頭列（`HTTP/1.1 200 OK` 等）都被縮排 → HTTP 回應格式不合法 → 瀏覽器當純文字顯示。
   此為 SP2 就沿用的舊寫法（老闆改過），非本次改動造成。

### UDP 模式補充觀察（已知；依使用者指示只記錄、不改程式）
UDP 設定模式：連上 Sam AP **之前**是正常水藍呼吸；**連上之後、收到 UDP message 之前**，水藍會凍住
（停在當下呼吸亮度、不再起伏）。同類根因：`UDP_Load_Wifi` 連上後進 `while True` 的 `udp_socket.recvfrom()`
阻塞、期間沒 `tick()`。此模式僅設定時短暫使用，不影響營運。

[返回主頁](README.md)
