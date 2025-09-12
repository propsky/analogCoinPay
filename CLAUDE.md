# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESP32 Smart Pay Board 2024 - MicroPython-based payment system for claw machines with coin detection, card reader integration, and WiFi management.

**Hardware**: ESP32 microcontroller  
**Language**: MicroPython  
**Current Version**: SP2_V0.20a  
**Main Branch**: main  
**Development Branch**: SP2_HWv1

## Architecture

### Core Components

- **analogCoinPay_Main.py** (810 lines): Main business logic, MQTT communication, state machine, hardware control
- **main.py** (254 lines): System initialization, GPIO setup, WiFi connection, emergency stop handling  
- **wifimgr.py** (262 lines): WiFi management, AP mode configuration, web interface for WiFi setup
- **Hardware Drivers**: BN165DKBDriver.py (keypad), lcd_manager.py (ST7735 LCD), mach_meter.py (counters)

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
- LCD Control: Pin 27 (backlight enable)
- Emergency Stop: SW1 via 74HC165 Data[3]

## Development Workflow

### Version Management

1. **Development**: Work in `sourceFiles/` directory
2. **Testing**: Test on hardware with new features
3. **Release**: Copy files to `releaseFiles/latestVersion/` for OTA updates
4. **Archive**: Create versioned ZIP file in `releaseFiles/`
5. **Documentation**: Update README.md with change log following the established format

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
- **Pulse Detection**: Eye sensor timing critical (0.01-0.8s for valid detection)
- **WiFi Delays**: 60-second delay on startup for 4G router initialization
- **Watchdog**: Regular WDT clearing required for system stability

### MQTT Integration

System publishes to MQTT broker with topics based on unique ESP32 ID:
- Device identification via SmartPay_[UniqueID] DHCP hostname
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

- **Emergency Stop**: SW1 button triggers immediate `sys.exit()`
- **Power Control**: Automatic shutdown of card reader and coin acceptor during OTA
- **Hardware Monitoring**: Continuous monitoring of claw machine fault detection
- **Interrupt Handling**: Debounced interrupt processing for coin detection and payout signals

## File Structure

```
├── sourceFiles/           # Development source code
├── releaseFiles/          
│   ├── latestVersion/     # OTA deployment files  
│   ├── SP2_V*.zip        # Version archives
│   └── *_ChangeList.md   # Version change documentation
├── push-check-list.md     # Pre-commit checklist
└── README.md             # Version history and todo list
```

## Hardware Dependencies

This codebase is specifically designed for Smart Pay Board V2 hardware and requires:
- 74HC165 shift register for input expansion
- ST7735 LCD display
- BN165DKB keypad interface
- Coin acceptor and payout mechanisms
- Card reader interface (optional)
- Various GPIO connections as defined in main.py