# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESP32 Smart Pay Board 2024 - MicroPython-based payment system for claw machines with coin detection, card reader integration, and WiFi management.

**Hardware**: ESP32 microcontroller  
**Language**: MicroPython  
**Current Version**: SP2_mpy_QR_V0.10a  
**Main Branch**: main  
**Development Branch**: SP2_HWv1_QR_mpy  
**MicroPython Firmware**: v1.18-9-gd8e35d0e0-dirty (2022-02-19)

## Architecture

### Core Components

- **analogCoinPay_Main.py / .mpy**: Main business logic, MQTT communication, state machine, hardware control, QR scanner UART handling. 部署時使用 .mpy（預編譯 bytecode）以解決記憶體限制問題
- **main.py**: System initialization, GPIO setup, WiFi connection, emergency stop handling. 先嘗試 execfile .py，失敗則 fallback 到 __import__ .mpy
- **wifimgr.py**: WiFi management, AP mode configuration, web interface for WiFi setup
- **config.json**: System configuration (boot delay, etc.)
- **Hardware Drivers**: BN165DKBDriver.py (keypad), lcd_manager.py (ST7735 LCD), mach_meter.py (counters)
- **mqtt-events-spec.md**: MQTT events 封包定義文件（qrscan、GiftOut）

### State Machine Architecture

MainStateMachine in analogCoinPay_Main.py manages system states:
- NONE_WIFI (0): No WiFi connection
- NONE_INTERNET (1): WiFi connected, no internet
- NONE_MQTT (2): Internet connected, no MQTT
- STANDBY_MQTT (7): Normal operation with MQTT
- GOING_TO_OTA (6): OTA update in progress

### GPIO Configuration

Key hardware interfaces defined in main.py:
- **GPO_CardReader_EPAY_EN** (Pin 2): 告訴卡機TV-1啟動或關閉刷卡功能
- **GPO_CardReader_PAYINOUT_EN** (Pin 19): 卡機訊號開關
- **GPO_QRScanner_UART_EN** (Pin 21): 掃碼器訊號開關（走UART）
- 電源邏輯：三者皆為0時才切斷卡機TV-1和掃碼器電源，只要有一個為1就維持供電
- Coin Acceptor: Pin 5 (power control)
- 74HC165 Shift Register: Pins 0, 32, 33 (keypad input)
- LCD Control: Pin 27 (backlight enable)
- Emergency Stop: SW1 via 74HC165 Data[3]
- QR Scanner UART: TX=22, RX=23, baudrate=115200

## Development Workflow

### Version Management

1. **Development**: Work in `sourceFiles/` directory
2. **Testing**: Test on hardware with new features
3. **Release**: Copy files to `releaseFiles/latestVersion/` for OTA updates
4. **Archive**: Create versioned ZIP file in `releaseFiles/`
5. **Documentation**: Update README.md with change log following the established format

### Deployment Commands

**Development Workflow:**
```bash
# 1. Update version in analogCoinPay_Main.py (line 1)
# 2. Test changes on hardware
# 3. Compile .mpy (MicroPython v1.18, mpy-cross v1.18.0)
mpy-cross sourceFiles/analogCoinPay_Main.py -o sourceFiles/analogCoinPay_Main.mpy
# 4. Deploy to OTA release directory
cp sourceFiles/* releaseFiles/latestVersion/
# 5. Create versioned backup
cd releaseFiles && zip -r SP2_V[version].zip latestVersion/
```

**MPY 編譯注意事項：**
- 使用 `pip install mpy-cross==1.18.0`
- .mpy 版本必須和韌體版本一致（v1.18），否則會報 `invalid mpy file`
- 每次修改 analogCoinPay_Main.py 後都需要重新編譯 .mpy
- main.py 不能編譯成 .mpy（開機只認 main.py）

### Push Checklist (from push-check-list.md)

Before committing changes:
1. Test on hardware (Smart Pay Board and claw machine)
2. Update version number in analogCoinPay_Main.py line 1
3. Review sourceFiles/ changes vs previous version
4. Copy sourceFiles/ to releaseFiles/latestVersion/
5. Create versioned ZIP backup in releaseFiles/
6. Update README.md code-change list with format:
   ```
   **YYYY/M/D_HW_Version_SW_Version, Author**
   1. Change description 1
   2. Change description 2
   * Based on previous_version
   ---
   ```

### Key Timing Considerations

- **utime module**: Used throughout for timing (避免溢位問題)
- **Pulse Detection**: Eye sensor timing critical (0.01-0.8s for valid detection), PAYOUT pulse 5-300ms (version dependent)
- **WiFi Delays**: Configurable startup delay via config.json boot_delay_sec (default 60s for 4G router, can be reduced to 1s for development)
- **Watchdog**: Regular WDT clearing required for system stability
- **Overflow Protection**: Use `utime.ticks_diff()` to handle timer overflow in pulse measurements

### MQTT Integration

System publishes to MQTT broker with topics based on unique ESP32 ID:
- Device identification via SmartPay_[UniqueID] DHCP hostname
- OTA updates triggered via MQTT commands
- Hardware state monitoring and remote control

**MQTT Events（即時事件封包）：**
Topic: `{cardid}/{token}/events`，訂閱用 `+/+/events`，以 `events` 欄位區分類型。
- `qrscan`：QR 掃碼通知，payload 含 `uuid`（36字元）和 `time`
- `GiftOut`：出獎通知，payload 含 `GiftOutQty`（可累積）和 `time`
- 詳見 `mqtt-events-spec.md`

**MQTT Event Flags 命名規則：**
`server_event_[功能]_flag` 或 `server_event_[功能]_Count`，統一在 `server_check_timer_callback()` 裡發送。

### Memory Management

- Explicit garbage collection (`gc.collect()`) after major operations
- Memory monitoring during development
- Module cleanup after initialization to free RAM
- **analogCoinPay_Main.py 因檔案過大（~37KB）在 ESP32 上記憶體碎片化無法直接執行**，需編譯成 .mpy（~17KB）使用
- main.py 執行邏輯：先 `execfile('analogCoinPay_Main.py')`，失敗則 `__import__('analogCoinPay_Main')`（載入 .mpy）
- analogCoinPay_Main.py 必須自己 import LCDManager（`from lcd_manager import LCDManager`），不能依賴 main.py 的 namespace

### WiFi Management

Dual-mode operation:
- **STA Mode**: Connect to configured WiFi network
- **AP Mode**: Fallback hotspot "HappyWifi[UniqueID]" for configuration
- **Web Interface**: HTTP server for WiFi credential setup

### Critical Safety Features

- **Emergency Stop**: SW1 button triggers immediate `sys.exit()`
- **Power Control**: Automatic shutdown of card reader and coin acceptor during OTA (via safe_reboot() function)
- **Hardware Monitoring**: Continuous monitoring of claw machine fault detection
- **Interrupt Handling**: Debounced interrupt processing for coin detection and payout signals

## File Structure

```
├── sourceFiles/           # Development source code
│   ├── analogCoinPay_Main.py  # Main application logic
│   ├── analogCoinPay_Main.mpy # 預編譯 bytecode（部署用）
│   ├── main.py               # System initialization
│   ├── config.json           # System configuration
│   ├── wifimgr.py           # WiFi management
│   ├── senko.py             # OTA update handler
│   └── *.py                 # Hardware drivers and utilities
├── releaseFiles/
│   ├── latestVersion/     # OTA deployment files
│   ├── SP2_V*.zip        # Version archives
│   └── *_ChangeList.md   # Version change documentation
├── mqtt-events-spec.md    # MQTT events 封包定義
├── push-check-list.md     # Pre-commit checklist
└── README.md             # Version history and todo list
```

## Recent Improvements (SP2_mpy_QR_V0.10a)

### WiFi QR Code Setup
- **parse_wifi_qr()**: Parses `WIFI:T:<auth>;S:<ssid>;P:<password>;H:<hidden>;;` format, validates WPA + non-empty SSID/password, writes `ssid;password\n` to wifi.dat, then calls `safe_reboot()`
- **Priority logic**: `uart_QRScanner_recive_packet_task()` checks `WIFI:` prefix first; UUID 36-char check only if not WiFi QR
- **Case-insensitive**: Uses `.upper().startswith("WIFI:")` to handle any-case QR generators
- **Fault guard bypass**: WiFi QR writing is allowed even when claw machine is in fault state (fault guard only blocks UUID MQTT)

### Bug Fixes
- **Integer division**: `Error_Code_of_Machine` calculation changed from `/` (float) to `//` (integer) to keep type consistent with `%100` and `*100` operations
- **Missing import**: Added `import gc` to main.py; `gc.collect()` / `gc.mem_free()` were called before any import
- **OTA branch**: main.py OTA branch corrected from `"SP2_HWv1"` to `"SP2_HWv1_QR_mpy"`

## Hardware Dependencies

This codebase is specifically designed for Smart Pay Board V2 hardware and requires:
- 74HC165 shift register for input expansion
- ST7735 LCD display
- BN165DKB keypad interface
- Coin acceptor and payout mechanisms
- Card reader interface (optional)
- Various GPIO connections as defined in main.py