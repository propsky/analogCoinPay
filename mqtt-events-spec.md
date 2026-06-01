# MQTT Events 封包定義

## 訂閱方式

所有 events 封包共用相同訂閱格式：

```
+/+/events
```

收到後依 `events` 欄位值判斷事件類型。

---

## 事件類型列表

| events 值 | 說明 | 狀態 |
|-----------|------|------|
| `qrscan` | QR 掃碼通知 | 已實作 |
| `GiftOut` | 出獎通知 | 已實作 |

---

## qrscan — QR 掃碼通知

### Topic
```
{cardid}/{token}/events
```

### Payload
```json
{
  "events": "qrscan",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "time": 154321000
}
```

### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `events` | string | 固定值 `"qrscan"` |
| `uuid` | string | QR Code 掃到的 UUID，標準格式 36 字元（含 `-`） |
| `time` | int | 裝置時間戳（Unix time，UTC+8） |

### 行為說明

- 每掃一次 QR Code 發一包，即時單次事件
- 娃娃機故障中不發送，完全忽略該次掃碼
- UUID 長度不等於 36 字元時，裝置端忽略並只印 log，不發送 MQTT
- 發送時機：掃碼成功後，最慢 1 秒內發出

---

## GiftOut — 出獎通知（規劃中）

### Topic
```
{cardid}/{token}/events
```

### Payload
```json
{
  "events": "GiftOut",
  "GiftOutQty": 1,
  "time": 154321000
}
```

### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `events` | string | 固定值 `"GiftOut"` |
| `GiftOutQty` | int | 本次出貨數量，目前固定為 1 |
| `time` | int | 裝置時間戳（Unix time，UTC+8） |

### 注意事項

- 每出獎一次發一包，即時單次事件
- `GiftOutQty` 與 `sales` 封包裡的 `GiftOuttimes`（累積總量）是不同欄位，請勿混用
- 實作上使用 `server_event_GiftOut_Count` 累加，支援短時間多次出獎，統一在 `server_check_timer_callback()` 發送
