# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESP32 Smart Pay Board 2024 - MicroPython-based payment system for claw machines with coin detection, card reader integration, and WiFi management.

本 branch 服務智付小卡 v2.1 硬體（co-layout 板上件 RGB LED，無 LCD）。

**Hardware**: ESP32 microcontroller  
**Language**: MicroPython  
**Firmware**: 官方 MicroPython v1.29.0（SP3 第一版改用官方韌體，取代原廠商客製 v1.18.9；評估見 SP3_韌體評估_目標v1.29.pdf）  
**Current Version**: SP3_V0.31a（正式定版）；程式碼同開發/OTA 測試碼 SP3_V0.01f，僅差版本字串與兩處註解（無行為變更）  
**Main Branch**: main（僅存放版本與 branch 索引，不含程式碼）  
**Development Branch**: SP3_HWv2.1

## Architecture

### Core Components

- **analogCoinPay_Main.py**: Main business logic, MQTT communication, state machine, hardware control
- **main.py**: System initialization, GPIO setup, WiFi connection, emergency stop handling
- **wifimgr.py**: WiFi management, AP mode configuration, web interface for WiFi setup
- **rgb_led_manager.py**: WS2812 單顆狀態燈（GPIO27，取代原 LCD）；規格與設計理由見 SP3_HWv2.1_RGB狀態燈規格與設計決策_rgb-led-spec.md
- **config.json**: System configuration (boot delay, etc.)
- **Hardware Drivers**: BN165DKBDriver.py (keypad), mach_meter.py (counters)

### State Machine Architecture

MainStateMachine in analogCoinPay_Main.py manages system states:
- NONE_WIFI (0): No WiFi connection
- NONE_INTERNET (1): WiFi connected, no internet
- NONE_MQTT (2): Internet connected, no MQTT
- STANDBY_MQTT (7): Normal operation with MQTT
- GOING_TO_OTA (6): OTA update in progress

### GPIO Configuration

Key hardware interfaces defined in main.py:
- Card Reader Control: Pins 2, 19, 21 (power and functionality control)
- Coin Acceptor: Pin 5 (power control)
- 74HC165 Shift Register: Pins 0, 32, 33 (keypad input)
- RGB LED (WS2812) status light: Pin 27（原 LCD 背光腳，LCD 移除後改用）
- Emergency Stop: SW1 via 74HC165 Data[3]

## Development Workflow

### Version Management

1. **Development**: Work in `sourceFiles/` directory
2. **Testing**: Test on hardware with new features
3. **Release**: Copy files to `releaseFiles/latestVersion/` for OTA updates
4. **Archive**: Create versioned ZIP file in `releaseFiles/`
5. **Documentation**: Update README.md with change log following the established format

> **Line endings**: `.gitattributes` 強制 *.py / *.json / *.md 為 LF，避免 CRLF 推上 GitHub。

### Deployment Commands

**Development Workflow:**
```bash
# 1. Update version in analogCoinPay_Main.py (line 1)
# 2. Test changes on hardware
# 3. Deploy to OTA release directory（排除 token.dat/wifi.dat 機台個資；若有刪檔如 lcd_manager.py 也要同步從 latestVersion 移除）
cp sourceFiles/*.py sourceFiles/config.json releaseFiles/latestVersion/
# 4. Create versioned backup（zip 內層資料夾以版本號命名，比照 SP2_V0.30b.zip）
cd releaseFiles && cp -r latestVersion SP3_V[version] && zip -r SP3_V[version].zip SP3_V[version] && rm -rf SP3_V[version]
```

### Push Checklist (from push-check-list.md)

Before committing changes:
1. Test on hardware (Smart Pay Board and claw machine)
2. Update version number in analogCoinPay_Main.py line 1
3. Review sourceFiles/ changes vs previous version
4. Copy sourceFiles/ to releaseFiles/latestVersion/（排除 token.dat/wifi.dat；同步移除已刪檔如 lcd_manager.py）
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
- **WiFi Delays**: Configurable startup delay via config.json boot_delay_sec（多數機台無 config 檔、走程式預設 3 秒；少數特殊機台放 config 檔設 60 秒）
- **Watchdog**: Regular WDT clearing required for system stability
- **Overflow Protection**: Use `utime.ticks_diff()` to handle timer overflow in pulse measurements

### MQTT Integration

System publishes to MQTT broker with topics based on unique ESP32 ID:
- Device identification via SmartPay_[UniqueID] DHCP hostname（新舊韌體設定 API 不同，wifimgr 依 network.hostname 是否存在自動分流）
- OTA updates triggered via MQTT commands
- Hardware state monitoring and remote control

### Memory Management

- Explicit garbage collection (`gc.collect()`) after major operations
- Memory monitoring during development
- Module cleanup after initialization to free RAM

### WiFi Management

Dual-mode operation:
- **STA Mode**: Connect to configured WiFi network
- **AP Mode**: Fallback hotspot "HappyWifi[UniqueID]" for configuration
- **Web Interface**: HTTP server for WiFi credential setup

### Critical Safety Features

- **Emergency Stop**: SW1 開機時按下 → `raise KeyboardInterrupt` 中止 main.py、乾淨掉到 REPL（原用 sys.exit()，因官方 v1.29 會被當 forced-exit 觸發 soft reset 迴圈而改）
- **Power Control**: Automatic shutdown of card reader and coin acceptor during OTA (via safe_reboot() function)
- **Hardware Monitoring**: Continuous monitoring of claw machine fault detection
- **Interrupt Handling**: Debounced interrupt processing for coin detection and payout signals

## File Structure

```
├── sourceFiles/           # Development source code
│   ├── analogCoinPay_Main.py  # Main application logic
│   ├── main.py               # System initialization
│   ├── config.json           # System configuration
│   ├── wifimgr.py           # WiFi management
│   ├── rgb_led_manager.py   # WS2812 狀態燈（取代 LCD）
│   ├── senko.py             # OTA update handler
│   └── *.py                 # Hardware drivers and utilities
├── releaseFiles/
│   ├── latestVersion/     # OTA deployment files
│   └── SP3_V*.zip         # Version archives（內層資料夾以版本號命名）
├── SP3_HWv2.1_RGB狀態燈規格與設計決策_rgb-led-spec.md   # 狀態燈規格與設計決策
├── push-check-list.md     # Pre-commit checklist
├── SP3_韌體評估_目標v1.29.pdf                 # 官方 v1.29 韌體相容性評估
├── SP3_HWv2.1_上機測試檢查清單和測試結果.md    # 上機驗證清單與結果（保留約半年參考）
└── README.md              # Version history and todo list
```

## Recent Changes（RGB LED 版，SP3_V0.31a 定版）

自 SP2_HWv1 的 SP2_V0.30b 拷貝建立 SP3 產品線（baseline＝SP3_V0.01a），之後在本 branch 上完成：

1. **RGB LED 狀態燈**：移除 LCD（刪除 lcd_manager.py），新增 rgb_led_manager.py 以單顆 WS2812（GPIO27）顯示系統狀態。十種燈號、被動式 tick 設計、狀態鎖（`set_state` 的 `lock` 參數）等規格見 SP3_HWv2.1_RGB狀態燈規格與設計決策_rgb-led-spec.md。
2. **韌體改官方 v1.29.0**：取代原廠商客製 v1.18.9（已棄養）；相容性/決策評估見 SP3_韌體評估_目標v1.29.pdf。
3. **DHCP 主機名分流**：wifimgr 依韌體自動選 API（新韌體 network.hostname()、舊韌體 dhcp_hostname），並在連線前一刻設定，確保後台顯示 SmartPay_xxxx。
4. **SW1 停止**：main.py 由 sys.exit() 改為 raise KeyboardInterrupt（避免 v1.29 的 soft-reset 迴圈；兩韌體通用）。

版號 SP3_V0.01a 起逐版遞增（開發中每次下載跳尾碼以確認最新），開發/OTA 測試碼為 SP3_V0.01f，正式定版 SP3_V0.31a（相對 SP3_V0.01f 僅差版本字串與兩處註解、無行為變更）。燈號、中斷完整性、記帳(IN/EPAY/OUT)、故障/電源、斷網、meter 持久化、長時間穩定度、OTA 流程皆已實機驗證通過。

## Hardware Dependencies

This codebase targets 智付小卡 v2.1 hardware and requires:
- 74HC165 shift register for input expansion
- WS2812 (NeoPixel) 單顆 RGB 狀態燈（GPIO27；取代原 ST7735 LCD）
- BN165DKB keypad interface
- Coin acceptor and payout mechanisms
- Card reader interface (optional)
- Various GPIO connections as defined in main.py