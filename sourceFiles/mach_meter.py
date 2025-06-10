# mach_meter.py (加入 reset_all_data)

import uos
import ujson

class MachMeter:
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
        self.data = {}
        self._load_data()

    def _load_data(self):
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
        try:
            with open(self._FILENAME, 'w') as f:
                ujson.dump(self.data, f)
            # print(f"資料成功儲存至 {self._FILENAME}")
        except OSError as e:
            print(f"錯誤：無法儲存資料到 {self._FILENAME}: {e}")

    # --- Increment Methods (回傳新值) ---
    def inc_in(self):
        self.data["IN"] = (self.data["IN"] + 1) % self._WRAP_VALUE
        return self.data["IN"]

    def inc_out(self):
        self.data["OUT"] = (self.data["OUT"] + 1) % self._WRAP_VALUE
        return self.data["OUT"]

    def inc_epay(self):
        self.data["EPAY"] = (self.data["EPAY"] + 1) % self._WRAP_VALUE
        return self.data["EPAY"]

    def inc_fplay(self):
        self.data["FPLAY"] = (self.data["FPLAY"] + 1) % self._WRAP_VALUE
        return self.data["FPLAY"]

    # --- Reset Methods (回傳新值, 也就是 0) ---
    def reset_in(self):
        self.data["IN"] = 0
        return self.data["IN"]

    def reset_out(self):
        self.data["OUT"] = 0
        return self.data["OUT"]

    def reset_epay(self):
        self.data["EPAY"] = 0
        return self.data["EPAY"]

    def reset_fplay(self):
        self.data["FPLAY"] = 0
        return self.data["FPLAY"]

    # --- Reset All Method (加入的新方法) ---
    def reset_all_data(self):
        self.data = self._DEFAULT_DATA.copy() # 將內部資料重設為預設值的副本
        return self.data.copy() # 回傳重設後資料的副本

    # --- Getter Methods ---
    def get_in(self):
        return self.data["IN"]

    def get_out(self):
        return self.data["OUT"]

    def get_epay(self):
        return self.data["EPAY"]

    def get_fplay(self):
        return self.data["FPLAY"]

    def get_all_data(self):
        return self.data.copy()

