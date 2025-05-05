# mach_meter.py

import ujson

class MachMeter:
    """
    一個管理計數器的類別，包含讀取、儲存、遞增和歸零功能。
    計數器會儲存在 'meter.json' 檔案中。
    遞增和歸零方法會回傳操作後的新數值。
    """
    _FILENAME = "meter.json"
    _MAX_VALUE = 65535
    _WRAP_VALUE = 65536

    _DEFAULT_DATA = {
        "IN": 0,
        "OUT": 0,
        "EPAY": 0,
        "FPLAY": 0
    }

    def __init__(self):
        """
        初始化 MachMeter 物件。
        嘗試載入 meter.json，如果檔案不存在則創建並寫入預設值。
        """
        self.data = {}
        self._load_data()

    def _load_data(self):
        """
        從 meter.json 載入資料。如果檔案不存在，則創建並載入預設值。
        """
        try:
            with open(self._FILENAME, 'r') as f:
                self.data = ujson.load(f)
            for key in self._DEFAULT_DATA:
                if key not in self.data:
                    print(f"警告: '{key}' 在 {self._FILENAME} 中不存在，將設定為預設值 0。")
                    self.data[key] = 0
            print(f"成功從 {self._FILENAME} 載入資料: {self.data}")
        except OSError as e:
            print(f"檔案 {self._FILENAME} 未找到或無法讀取 ({e}). 將創建新檔案並使用預設值。")
            self.data = self._DEFAULT_DATA.copy()
            self.save()

    def save(self):
        """
        將目前的計數器數值儲存回 meter.json 檔案。
        """
        try:
            with open(self._FILENAME, 'w') as f:
                ujson.dump(self.data, f)
            # print(f"資料成功儲存至 {self._FILENAME}")
        except OSError as e:
            print(f"錯誤：無法儲存資料到 {self._FILENAME}: {e}")

    # --- Increment Methods (回傳新值) ---
    def inc_in(self):
        """將 IN 計數器加一，達到最大值後歸零，並回傳新的計數值。"""
        self.data["IN"] = (self.data["IN"] + 1) % self._WRAP_VALUE
        return self.data["IN"] # 回傳更新後的值

    def inc_out(self):
        """將 OUT 計數器加一，達到最大值後歸零，並回傳新的計數值。"""
        self.data["OUT"] = (self.data["OUT"] + 1) % self._WRAP_VALUE
        return self.data["OUT"] # 回傳更新後的值

    def inc_epay(self):
        """將 EPAY 計數器加一，達到最大值後歸零，並回傳新的計數值。"""
        self.data["EPAY"] = (self.data["EPAY"] + 1) % self._WRAP_VALUE
        return self.data["EPAY"] # 回傳更新後的值

    def inc_fplay(self):
        """將 FPLAY 計數器加一，達到最大值後歸零，並回傳新的計數值。"""
        self.data["FPLAY"] = (self.data["FPLAY"] + 1) % self._WRAP_VALUE
        return self.data["FPLAY"] # 回傳更新後的值

    # --- Reset Methods (回傳新值, 也就是 0) ---
    def reset_in(self):
        """將 IN 計數器歸零，並回傳 0。"""
        self.data["IN"] = 0
        return self.data["IN"] # 回傳 0

    def reset_out(self):
        """將 OUT 計數器歸零，並回傳 0。"""
        self.data["OUT"] = 0
        return self.data["OUT"] # 回傳 0

    def reset_epay(self):
        """將 EPAY 計數器歸零，並回傳 0。"""
        self.data["EPAY"] = 0
        return self.data["EPAY"] # 回傳 0

    def reset_fplay(self):
        """將 FPLAY 計數器歸零，並回傳 0。"""
        self.data["FPLAY"] = 0
        return self.data["FPLAY"] # 回傳 0

    def reset_all_data(self):
        """將所有計數器歸零，並回傳"""
        self.data = self._DEFAULT_DATA.copy()
        return self.data.copy()

    # --- Getter Methods ---
    def get_in(self):
        """取得目前的 IN 計數值。"""
        return self.data["IN"]

    def get_out(self):
        """取得目前的 OUT 計數值。"""
        return self.data["OUT"]

    def get_epay(self):
        """取得目前的 EPAY 計數值。"""
        return self.data["EPAY"]

    def get_fplay(self):
        """取得目前的 FPLAY 計數值。"""
        return self.data["FPLAY"]

    def get_all_data(self):
        """取得包含所有計數值的字典。"""
        return self.data.copy()

# --- 如何在您的主程式中使用 (示範接收回傳值) ---
# 假設您將上面的程式碼儲存為 mach_meter.py

# 在您的 main.py 或其他主程式檔案中:
# from mach_meter import MachMeter

# meter = MachMeter()
# print("初始值:", meter.get_all_data())

# # 使用 inc 方法並接收回傳值
# new_in_value = meter.inc_in()
# print(f"投幣一次後，新的 IN 值: {new_in_value}")
# print(f"再次投幣後，新的 IN 值: {meter.inc_in()}") # 也可以直接印出回傳值

# new_epay_value = meter.inc_epay()
# print(f"電子支付一次後，新的 EPAY 值: {new_epay_value}")

# print("目前所有值:", meter.get_all_data())

# # 使用 reset 方法並接收回傳值 (會是 0)
# reset_in_value = meter.reset_in()
# print(f"重設 IN 後的值: {reset_in_value}")

# print("重設後所有值:", meter.get_all_data())

# meter.save()
# print("數值已儲存至 meter.json")