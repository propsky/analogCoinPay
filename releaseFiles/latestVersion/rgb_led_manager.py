# rgb_led_manager.py
# WS2812 單顆狀態指示燈（SP3 智付小卡 v2.1，GPIO27）
# 被動式：外部需定期呼叫 tick() 推進動畫，本模組不使用 timer / thread。
# 燈號規格、設計理由、阻塞點清單：見 rgb-led-spec.md

import utime
import machine

# ===== 硬體參數（放檔案開頭方便調整）=====
LED_STATUS_PIN = 27     # WS2812 資料腳位（原 LCD_EN 背光致能，LCD 移除後釋出）
LED_STATUS_NUM = 1      # 燈珠數量（本硬體固定 1 顆，程式只驅動 np[0]）
LED_BRIGHTNESS = 25     # 全域亮度上限 0~255。壓低是為了防手機錄影過曝，不只是不刺眼


class RGBLEDManager:
    """WS2812 單顆狀態燈，單例。"""

    _instance = None

    # ===== 十種狀態常數（用法：RGBLEDManager.RUNNING）=====
    BOOT_TEST     = 'BOOT_TEST'      # 上電自檢：紅->綠->藍，由 boot_test() 阻塞執行
    BOOTING       = 'BOOTING'        # 開機中：白，呼吸，週期 2000ms
    WIFI_CONFIG   = 'WIFI_CONFIG'    # Wi-Fi 設定模式：水藍，呼吸，週期 1000ms
    WIFI_CONNECTING = 'WIFI_CONNECTING'  # Wi-Fi 連線嘗試中：紅，呼吸2s（還在試、未有結論；不同於閃1下的 NO_WIFI）
    NO_WIFI       = 'NO_WIFI'        # 沒有 Wi-Fi：紅，閃 1 下
    NO_MQTT       = 'NO_MQTT'        # 沒有 MQTT：黃，閃 2 下
    MACHINE_FAULT = 'MACHINE_FAULT'  # 娃娃機故障：紫，閃 3 下
    RUNNING       = 'RUNNING'        # 正常運行：綠，呼吸，週期 2000ms
    UPDATING_REBOOTING = 'UPDATING_REBOOTING'  # OTA 更新 / 重開機：白，恆亮（期間阻塞不 tick，無法閃動故用恆亮）
    STOPPED       = 'STOPPED'        # 停止：紅，恆亮

    # ===== 顏色（全值 RGB。WS2812 的 GRB 排序交給 neopixel 模組處理，這裡傳 (R,G,B)）=====
    _RED     = (255, 0,   0)
    _GREEN   = (0,   255, 0)
    _BLUE    = (0,   0,   255)
    _WHITE   = (255, 255, 255)
    _WATER_BLUE = (0, 180, 255)   # 水藍
    _YELLOW  = (255, 255, 0)
    _PURPLE  = (160, 0,   255)   # 紫

    # ===== 節奏參數（規格，勿改）=====
    _BLINK_ON_MS  = 150     # 閃爍：亮的長度
    _BLINK_OFF_MS = 150     # 閃爍：每下之間暗的長度
    _BLINK_GAP_MS = 1000    # 閃爍：N 下閃完後、下一輪前的全暗停頓（用來隔開兩組，方便數次數）
    _FAST_HALF_MS = 125     # 快閃 4Hz => 週期 250ms => 半週期 125ms
    _BREATHE_MIN  = 0.08    # 呼吸最低亮度（永不全暗，區別於閃爍類）

    # ===== 狀態 -> 燈效規格表 =====
    # 格式：state: (類型, 顏色, 參數)
    #   'breathe' 呼吸       參數 = 週期ms
    #   'blink'   閃 N 下     參數 = 次數 N（每下 亮150+暗150，N 下後全暗停1000）
    #   'fast'    快閃 4Hz    參數 = None
    #   'solid'   恆亮        參數 = None
    # 註：BOOT_TEST 不在此表，改由 boot_test() 阻塞式執行。
    _SPEC = {
        BOOTING:       ('breathe', _WHITE,   2000),
        WIFI_CONFIG:   ('breathe', _WATER_BLUE, 1000),
        WIFI_CONNECTING: ('breathe', _RED,   2000),
        RUNNING:       ('breathe', _GREEN,   2000),
        NO_WIFI:       ('blink',   _RED,     1),
        NO_MQTT:       ('blink',   _YELLOW,  2),
        MACHINE_FAULT: ('blink',   _PURPLE,  3),
        UPDATING_REBOOTING: ('solid', _WHITE,  None),
        STOPPED:       ('solid',   _RED,     None),
    }

    @classmethod
    def get_instance(cls):
        """取得單例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if RGBLEDManager._instance is not None:
            raise Exception("這是單例類別，請使用 get_instance() 取得實例")
        # 延遲初始化屬性（真正的硬體物件在 initialize() 才建立）
        self.np = None            # neopixel 物件，None 代表未初始化或初始化失敗
        self._brightness = LED_BRIGHTNESS
        self._state = None        # 目前狀態
        self._anim_start = 0      # 動畫相位錨點（ticks_ms），set_state() 時歸零
        self._last_rgb = None     # 上次實際寫入燈珠的值，用來避免同色重寫（約束3）
        self._flash_color = None  # flash 覆蓋層顏色（本版保留不使用）
        self._flash_until = 0     # flash 覆蓋層到期時間（ticks_ms）
        self._locked = False      # True＝鎖定中，一般 set_state 會被忽略（見 set_state 的 lock）

    def initialize(self, pin=LED_STATUS_PIN, num=LED_STATUS_NUM, brightness=LED_BRIGHTNESS):
        """初始化 WS2812；已初始化則略過；失敗只記 log、不拋例外、不 reset。"""
        if self.np is not None:
            print("RGB LED 已初始化，略過重複 initialize()")
            return
        self._brightness = brightness
        try:
            import neopixel  # 放在 try 內，才能攔到「neopixel 模組不存在」的情況
            self.np = neopixel.NeoPixel(machine.Pin(pin), num)
            print("RGB LED 初始化完成, pin=%d, num=%d, brightness=%d" % (pin, num, brightness))
        except Exception as e:
            self.np = None
            print("RGB LED 初始化失敗（狀態燈停用，不影響營運）:", e)

    # ---------- 內部工具 ----------

    def _scale(self, color, intensity):
        """底色 × 全域亮度 × intensity(0~1) => 實際燈珠 (r,g,b)。"""
        b = self._brightness / 255.0
        return (int(color[0] * b * intensity),
                int(color[1] * b * intensity),
                int(color[2] * b * intensity))

    def _output(self, rgb):
        """把 (r,g,b) 寫進燈珠；與上次相同就不重寫（省關中斷開銷，見 rgb-led-spec.md）。"""
        if self.np is None:
            return
        if rgb == self._last_rgb:
            return
        self.np[0] = rgb
        self.np.write()
        self._last_rgb = rgb

    def _render(self, now):
        """依目前狀態與時間 now，算出並輸出「一幀」。"""
        if self.np is None:
            return

        # flash 覆蓋層優先（本版保留不使用，供日後現場除錯）
        if self._flash_color is not None:
            if utime.ticks_diff(self._flash_until, now) > 0:
                self._output(self._scale(self._flash_color, 1.0))
                return
            self._flash_color = None  # 覆蓋層已到期，往下走正常狀態

        spec = self._SPEC.get(self._state)
        if spec is None:
            return
        kind, color, param = spec

        # 相位一律用時間推算（不靠 tick 被呼叫幾次），並用 ticks_diff 處理溢位（約束2）
        elapsed = utime.ticks_diff(now, self._anim_start)

        if kind == 'solid':
            # 恆亮：固定滿強度。寫一次後靠 _output 的同色判斷不再重寫。
            self._output(self._scale(color, 1.0))

        elif kind == 'breathe':
            # 呼吸：三角波 0->1->0，再映射到 0.08~1.0（永不全暗）
            period = param
            phase = elapsed % period
            half = period / 2
            tri = phase / half if phase < half else (period - phase) / half
            intensity = self._BREATHE_MIN + (1.0 - self._BREATHE_MIN) * tri
            self._output(self._scale(color, intensity))

        elif kind == 'blink':
            # 閃 N 下：一個週期 = (亮150+暗150)×N + 全暗停1000
            n = param
            unit = self._BLINK_ON_MS + self._BLINK_OFF_MS   # 一下的長度(300)
            group = unit * n                                # N 下閃爍段總長
            period = group + self._BLINK_GAP_MS             # 再加尾端停頓
            phase = elapsed % period
            if phase < group:
                pos = phase % unit                          # 落在某一下之內的位置
                intensity = 1.0 if pos < self._BLINK_ON_MS else 0.0
            else:
                intensity = 0.0                             # 尾端全暗停頓
            self._output(self._scale(color, intensity))

        elif kind == 'fast':
            # 快閃 4Hz：亮125 + 暗125
            phase = elapsed % (self._FAST_HALF_MS * 2)
            intensity = 1.0 if phase < self._FAST_HALF_MS else 0.0
            self._output(self._scale(color, intensity))

    # ---------- 對外介面 ----------

    def set_state(self, state, lock=None):
        """設定狀態並立即畫一幀。lock 三態（規格見 rgb-led-spec.md）：
        lock=None（不餵）：一般模式，已鎖則忽略；同狀態不重設相位。
        lock=True：強制執行並上鎖（之後除了 lock=False 解鎖，誰都蓋不掉）。
        lock=False：強制執行並解鎖。"""
        if self._locked and lock is not False:  # 鎖定中：只有明確解鎖(lock=False)放行
            return
        if lock is None and state == self._state:  # 未鎖的一般呼叫：同狀態不重設相位
            return
        self._state = state
        self._anim_start = utime.ticks_ms()
        self._last_rgb = None
        self._render(self._anim_start)
        if lock is True:
            self._locked = True
        elif lock is False:
            self._locked = False

    def tick(self):
        """推進動畫，不阻塞。需外部定期呼叫（20~50Hz）。"""
        if self._state is None:
            return
        self._render(utime.ticks_ms())

    def boot_test(self):
        """上電自檢：紅→綠→藍各 500ms（阻塞 1500ms，僅一輪）。"""
        if self.np is None:
            return
        for color in (self._RED, self._GREEN, self._BLUE):
            self._output(self._scale(color, 1.0))
            utime.sleep_ms(500)
        self.off()

    def flash(self, color, duration_ms):
        """瞬間事件的暫時覆蓋層（duration_ms 內覆蓋正常狀態）；本版保留未使用。"""
        self._flash_color = color
        self._flash_until = utime.ticks_add(utime.ticks_ms(), duration_ms)
        self._render(utime.ticks_ms())

    def off(self):
        """熄滅燈珠。"""
        self._output((0, 0, 0))

    def cleanup(self):
        """釋放資源。"""
        self.off()
        self.np = None
        RGBLEDManager._instance = None
