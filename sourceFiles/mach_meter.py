# mach_meter.py (加入 reset_all_data)

import uos
import ujson

class MachMeter:
    """
    一個管理計數器的類別，包含讀取、儲存、遞增和歸零功能。
    計數器會儲存在 'meter.json' 檔案中。
    提供單項或全部計數器的遞增/歸零方法。
    遞增和歸零方法會回傳操作後的新數值 (單項歸零回傳 0，全部歸零回傳包含所有 0 的字典)。

    主要方法:
    - __init__(): 初始化，載入或創建 meter.json。
    - save(): 將目前數值存檔。
    - inc_in(), inc_out(), inc_epay(), inc_fplay(): 對應計數器加一並回傳新值 (溢位歸零)。
    - reset_in(), reset_out(), reset_epay(), reset_fplay(): 對應計數器歸零並回傳 0。
    - reset_all_data(): 將所有計數器歸零並回傳包含所有 0 的字典。
    - get_in(), get_out(), get_epay(), get_fplay(): 取得對應計數器的值。
    - get_all_data(): 取得包含所有計數器值的字典。
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
        return self.data["IN"]

    def inc_out(self):
        """將 OUT 計數器加一，達到最大值後歸零，並回傳新的計數值。"""
        self.data["OUT"] = (self.data["OUT"] + 1) % self._WRAP_VALUE
        return self.data["OUT"]

    def inc_epay(self):
        """將 EPAY 計數器加一，達到最大值後歸零，並回傳新的計數值。"""
        self.data["EPAY"] = (self.data["EPAY"] + 1) % self._WRAP_VALUE
        return self.data["EPAY"]

    def inc_fplay(self):
        """將 FPLAY 計數器加一，達到最大值後歸零，並回傳新的計數值。"""
        self.data["FPLAY"] = (self.data["FPLAY"] + 1) % self._WRAP_VALUE
        return self.data["FPLAY"]

    # --- Reset Methods (回傳新值, 也就是 0) ---
    def reset_in(self):
        """將 IN 計數器歸零，並回傳 0。"""
        self.data["IN"] = 0
        return self.data["IN"]

    def reset_out(self):
        """將 OUT 計數器歸零，並回傳 0。"""
        self.data["OUT"] = 0
        return self.data["OUT"]

    def reset_epay(self):
        """將 EPAY 計數器歸零，並回傳 0。"""
        self.data["EPAY"] = 0
        return self.data["EPAY"]

    def reset_fplay(self):
        """將 FPLAY 計數器歸零，並回傳 0。"""
        self.data["FPLAY"] = 0
        return self.data["FPLAY"]

    # --- Reset All Method (加入的新方法) ---
    def reset_all_data(self):
        """將所有計數器歸零 (重設為預設值)，並回傳包含所有新值 (0) 的字典副本。"""
        self.data = self._DEFAULT_DATA.copy() # 將內部資料重設為預設值的副本
        return self.data.copy() # 回傳重設後資料的副本

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
        """取得包含所有計數值的字典副本。"""
        return self.data.copy()

