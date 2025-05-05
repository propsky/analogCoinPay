# code-change list


**2025/5/5V1.OO, Sam**
目前當wifi正確可以上傳，切換到下一隻程式，rtc也正常，
但可能要處理 ota 路徑和當wifi有問題的狀況。
另外，投幣資料json還沒處理

**2025/3/5_SP2_V0.01a, Thomas**
1. 以智付小卡硬體V1.0開發，刪除smartpay1 SPHP_V1.00c的FEILOLI UART
2. MQTT暫時可以上傳了，但還有許多未修改確認部分，可能有BUG
* Based on smartpay1 2025/3/5_SPHP_V1.00c, Thomas
---

以下是新增的mach_meter.py使用方法
# MachMeter for MicroPython (ESP32)

這是一個用於 ESP32 (MicroPython) 的計數器管理類別，可以將計數資料 (IN, OUT, EPAY, FPLAY) 持久化儲存到 `meter.json` 檔案中。

## 功能

* 初始化時自動載入或創建 `meter.json` 檔案。
* 提供 `inc_` 方法對各項計數器加一 (最大值 65535，溢位歸零)，並回傳新值。
* 提供 `reset_` 方法對各項計數器歸零，並回傳 0。
* 提供 `reset_all_data()` 方法將所有計數器歸零，並回傳包含新值的字典。
* 提供 `save()` 方法將目前的計數器狀態儲存回 `meter.json`。
* 提供 `get_` 方法取得目前的計數器值。

## 如何使用

1.  將 `mach_meter.py` 檔案上傳到您的 ESP32 裝置。
2.  在您的主程式 (例如 `main.py`) 中匯入並使用它。

### 範例程式碼 (`main.py`)

以下是如何在您的主程式中使用 `MachMeter` 類別的範例：

```python
# 假設您已經將 mach_meter.py 上傳到 ESP32

# 在您的 main.py 或其他主程式檔案中:
from mach_meter import MachMeter
import time

# 1. 創建 MachMeter 物件
#    這會自動檢查 meter.json 或創建它
print("正在初始化 MachMeter...")
meter = MachMeter()
print("初始值:", meter.get_all_data())
time.sleep(1) # 暫停一下方便觀察

# 2. 操作一些計數器
print("\n操作計數器...")
new_in = meter.inc_in()
print(f"  - 執行 inc_in(), 新 IN 值: {new_in}")
new_epay = meter.inc_epay()
print(f"  - 執行 inc_epay(), 新 EPAY 值: {new_epay}")
new_fplay = meter.inc_fplay()
print(f"  - 執行 inc_fplay(), 新 FPLAY 值: {new_fplay}")

print("操作後的值:", meter.get_all_data())
time.sleep(1)

# 3. 儲存一下目前的狀態
#    建議在數值有變更後，或系統準備關閉/重啟前執行
print("\n儲存目前狀態...")
meter.save()
print("數值已儲存至 meter.json。")
time.sleep(1)

# (可以嘗試斷電重啟 ESP32，然後重新執行此腳本，
#  看看初始值是否為剛剛儲存的值)

print("-" * 20)

# 4. 使用 reset_all_data 方法
print("\n準備重設所有計數器...")
reset_values = meter.reset_all_data()
print(f"  - reset_all_data() 回傳的值: {reset_values}")
print(f"  - 重設後，透過 get_all_data() 取得的值: {meter.get_all_data()}")
time.sleep(1)

# 5. 重設後記得儲存，才會將歸零狀態寫入檔案
print("\n儲存重設後的狀態...")
meter.save()
print("重設後的值已儲存至 meter.json")

print("\n範例執行完畢。")