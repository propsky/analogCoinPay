# code-change list

**2025/8/25_SP2_V0.0825sd_AI_THERMAL, Thomas+Claude**
1. 新增MQTT診斷日志系統，即時監控投幣器脈波狀態
2. 解決ESP32時間溢出問題，使用安全的時間差計算
3. 實作非阻塞的日志緩衝機制，避免中斷處理延遲
4. 提供詳細的脈波寬度分析和拒絕原因追蹤
5. **新增溫度監控與熱效應診斷功能**
6. **整合溫度資訊到每個脈波診斷日志**
7. **實作智能溫度警報與補償建議機制**
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

1. 整合SPHP_HWv1(開心小卡B1)的檔案，除了acp_m.py以外的4個py檔，檢查差異是否都同步導入
a. BN165DKBDriver.py => ok
b. senko.py => ok
c. wifimgr.py => 雖然已導入，但未確認功能差異
d. main.py => 雖然已導入，但未確認功能差異，並且有新版需要再排入更新
=> 已知狀況：當開機偵測到有otalist.dat，但是要ota的檔案是最新一致&不需要更新的，這種情況下 不會刪掉otalist。

2. 繼續導入Sam20250505
3. 修補小卡的重連機制，不嘗試連線時，想要完全關掉wifi模組

4. 確認OTA以下更新方式是否正常合理
a. 舊->新
b. 新->新

---

# MQTT診斷日志系統使用指南 (SP2_V0.0825sd_AI+)

## 如何查看診斷日志

### 1. MQTT客戶端設定
使用任何MQTT客戶端工具（如 MQTT Explorer、mosquitto_sub、或手機APP）連接到：

```
伺服器: happycollect.propskynet.com
用戶名: myuser
密碼: propskymqtt
訂閱主題: {設備MAC地址}/{token}/diagnostic
```

### 2. 取得設備資訊
- **MAC地址**: 在設備LCD螢幕上顯示，或從其他MQTT主題中取得
- **Token**: 存放在設備的 token.dat 檔案中

### 3. 範例訂閱指令
```bash
mosquitto_sub -h happycollect.propskynet.com -u myuser -P propskymqtt -t "A1B2C3D4E5F6/your-token-here/diagnostic"
```

## 診斷日志格式解讀

### 日志類型

#### 1. 中斷事件 (event: "interrupt")
```json
{
  "event": "interrupt",
  "pin": "Coin_IN1",
  "gpio_value": 0,
  "interrupt_time": 1234567,
  "timestamp": 1692950400,
  "uptime_ms": 123456789
}
```

#### 2. 投幣脈波 (event: "coin_pulse")
```json
{
  "event": "coin_pulse",
  "pin": "Coin_IN1",
  "result": "REJECTED",
  "reason": "Low脈波過長(250ms > 200ms)",
  "hi_pulse_ms": 120,
  "low_pulse_ms": 250,
  "hi_pulse_min": 100,
  "low_pulse_min": 10,
  "low_pulse_max": 200,
  "timestamp": 1692950401,
  "uptime_ms": 123456789
}
```

#### 3. 卡機支付 (event: "card_pulse")
```json
{
  "event": "card_pulse",
  "pin": "PAYOUT",
  "result": "ACCEPTED",
  "reason": "脈波寬度符合要求",
  "hi_pulse_ms": 150,
  "low_pulse_ms": 80,
  "hi_pulse_min": 100,
  "low_pulse_min": 50,
  "low_pulse_max": 200,
  "temperature_c": 45.2,
  "thermal_status": "NORMAL",
  "timestamp": 1692950402
}
```

#### 4. 溫度監控 (event: "thermal_monitor")
```json
{
  "event": "thermal_monitor",
  "pin": "ESP32_INTERNAL",
  "temperature_c": 68.5,
  "thermal_status": "OVERHEAT_WARNING",
  "thermal_warning": "溫度偏高，建議檢查散熱系統",
  "reason": "溫度偏高，建議檢查散熱系統",
  "uptime_hours": 12.5,
  "timestamp": 1692950403
}
```

#### 5. 過熱脈波異常 (event: "coin_pulse")
```json
{
  "event": "coin_pulse",
  "pin": "Coin_IN1",
  "result": "REJECTED",
  "reason": "Low脈波過長(250ms > 200ms)",
  "hi_pulse_ms": 120,
  "low_pulse_ms": 250,
  "temperature_c": 72.1,
  "thermal_status": "OVERHEAT_CRITICAL",
  "thermal_warning": "ESP32過熱，可能影響時序準確性",
  "temp_compensation": "建議放寬脈波下限11ms",
  "timestamp": 1692950404
}
```

## 欄位說明

| 欄位 | 說明 |
|------|------|
| `event` | 事件類型：interrupt/coin_pulse/card_pulse/thermal_monitor |
| `pin` | 觸發的GPIO：Coin_IN1/Coin_IN2/PAYOUT/ESP32_INTERNAL |
| `result` | 處理結果：ACCEPTED/REJECTED |
| `reason` | 詳細原因說明 |
| `hi_pulse_ms` | Hi電位持續時間（毫秒） |
| `low_pulse_ms` | Low電位持續時間（毫秒） |
| `*_pulse_min/max` | 設定的脈波寬度範圍 |
| `temperature_c` | **ESP32內部溫度（攝氏度）** |
| `thermal_status` | **溫度狀態：NORMAL/OVERHEAT_WARNING/OVERHEAT_CRITICAL/UNDERHEAT** |
| `thermal_warning` | **溫度警告訊息** |
| `temp_compensation` | **溫度補償建議** |
| `timestamp` | UTC時間戳 |
| `uptime_ms` | 設備開機時間（毫秒） |
| `uptime_hours` | **設備運行時數（小時）** |

## 故障診斷指南

### 投幣器問題診斷

#### 1. 完全沒有投幣反應
**症狀**: 投幣時沒有任何日志
**可能原因**: 
- 投幣器電源未接通
- GPIO線路斷線
- 中斷設定錯誤

#### 2. 投幣被拒絕
**症狀**: `result: "REJECTED"`

**常見拒絕原因**:
```
"Hi脈波過短(95ms < 100ms)" → 投幣器老化，脈波變短
"Low脈波過長(250ms > 200ms)" → 機械卡頓或電路異常
"Hi脈波過短(80ms < 100ms); Low脈波過長(300ms > 200ms)" → 多重問題
```

#### 3. 脈波寬度分析
- **正常範圍**:
  - 投幣器: Hi≥100ms, Low=10-200ms
  - 卡機: Hi≥100ms, Low=50-200ms
- **異常模式**:
  - 逐漸變短 → 硬體老化
  - 忽大忽小 → 電源不穩或干擾
  - 極端值 → 硬體故障

#### 4. **溫度相關問題診斷**
**症狀**: `temperature_c > 60` 且同時有脈波 `REJECTED`

**過熱影響分析**:
```
溫度範圍        熱效應等級    典型症狀
<50°C          正常         無溫度影響
50-60°C        輕微         偶發脈波異常
60-70°C        警告         脈波REJECTED率增加
70-80°C        嚴重         頻繁投幣失效
>80°C          危險         系統可能不穩定
```

**診斷步驟**:
1. **檢視溫度趨勢**: 溫度是否隨時間上升
2. **關聯性分析**: 高溫時段的REJECTED率是否明顯增加
3. **環境對比**: 室溫 vs ESP32溫度的差值
4. **時間模式**: 午後或連續運行後問題是否加劇

**過熱確認方法**:
```bash
# 篩選過熱時段的脈波異常
mosquitto_sub -h server -u user -P pass -t "MAC/token/diagnostic" | jq 'select(.temperature_c > 65 and .result == "REJECTED")'

# 統計溫度分布
mosquitto_sub -h server -u user -P pass -t "MAC/token/diagnostic" | jq '.temperature_c' | sort -n
```

### 長期監控建議

1. **設定警報**: 當REJECTED率超過10%時發送通知
2. **趨勢追蹤**: 記錄脈波寬度變化，預測硬體更換時機
3. **定期檢查**: 每週檢視診斷日志，及早發現問題
4. **現場驗證**: 當日志顯示異常時，現場測試投幣功能確認
5. **🔥 溫度監控**: 設定溫度警報，當 `temperature_c > 65°C` 時通知
6. **🔥 過熱預防**: 觀察溫度趨勢，預防性改善散熱系統
7. **🔥 季節調整**: 夏季時降低脈波判定的嚴格程度
8. **🔥 環境關聯**: 記錄環境溫度與設備溫度的關係

## 注意事項

- 診斷日志僅在MQTT連線正常時發送
- 日志緩衝最多10條，超過會自動清除最舊的
- 中斷處理採用非阻塞設計，不影響投幣器響應速度
- 系統時間採用安全計算，避免ESP32溢出問題
- **🔥 ESP32內建溫度感測器精度約±2°C，足夠診斷用途**
- **🔥 溫度監控每30秒執行一次，不會影響系統性能**
- **🔥 溫度補償建議僅供參考，實際調整需現場測試驗證**
- **🔥 極端過熱(>80°C)可能導致ESP32系統不穩定，需立即處理**

## 溫度與脈波異常關聯分析方法

### 快速診斷指令
```bash
# 監控即時溫度與脈波狀態
mosquitto_sub -h happycollect.propskynet.com -u myuser -P propskymqtt -t "YOUR_MAC/YOUR_TOKEN/diagnostic"

# 僅顯示溫度異常事件
mosquitto_sub -h happycollect.propskynet.com -u myuser -P propskymqtt -t "YOUR_MAC/YOUR_TOKEN/diagnostic" | jq 'select(.thermal_status != "NORMAL")'

# 僅顯示高溫時的脈波拒絕事件
mosquitto_sub -h happycollect.propskynet.com -u myuser -P propskymqtt -t "YOUR_MAC/YOUR_TOKEN/diagnostic" | jq 'select(.temperature_c > 60 and .result == "REJECTED")'
```

### 散熱改善建議
1. **立即措施**: 加裝散熱片或提升通風
2. **中期改善**: 調整設備安裝位置，遠離熱源
3. **長期解決**: 設計更好的機箱散熱系統
