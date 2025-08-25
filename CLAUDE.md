# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

這是一個 ESP32 MicroPython 專案，用於類比投幣支付系統（analogCoinPay），支援娃娃機等遊戲機台的投幣、卡機、電眼偵測等功能。

## 開發環境

- 平台：ESP32 微控制器
- 語言：MicroPython
- 硬體架構：智付小卡 SP2 (SmartPay2) 硬體版本

## 檔案結構與架構

### 主要目錄

- `sourceFiles/`：主要原始碼檔案
- `releaseFiles/`：發行版本檔案
  - `latestVersion/`：最新版本檔案，用於 OTA 更新
- `push-check-list.md`：發布前檢查清單

### 核心模組

1. **main.py**：系統啟動入口點
   - GPIO 初始化（卡機、投幣器、電眼等）
   - WiFi 連線管理
   - NTP 時間同步
   - OTA 更新檢查
   - 啟動主程式

2. **analogCoinPay_Main.py**：主要業務邏輯
   - 狀態機管理（MainStateMachine）
   - MQTT 通訊
   - 投幣偵測與處理
   - 電眼狀態監控

3. **lcd_manager.py**：LCD 顯示管理（單例模式）
   - ST7735 LCD 驅動控制
   - 文字顯示與色彩管理

4. **wifimgr.py**：WiFi 管理
   - STA 模式連線
   - AP 模式設定
   - 網路狀態監控

5. **mach_meter.py**：機台計數器管理
   - IN/OUT/EPAY/FPLAY 計數
   - JSON 檔案持久化儲存

6. **senko.py**：OTA (Over-The-Air) 更新模組
   - GitHub repository 整合
   - 韌體遠端更新

## 硬體 GPIO 配置

- **卡機控制**：Pin 2, 19, 21（電源與功能控制）
- **投幣器控制**：Pin 5
- **電眼訊號**：Pin 17 (FEILOLI)
- **LCD 控制**：Pin 27 (EN), Pin 14 (SCK), Pin 13 (MOSI)
- **165D 鍵盤**：Pin 32 (PL), Pin 33 (Q7), Pin 0 (CP/CE)

## 版本管理

### 版本號格式
- 硬體架構：SP2 (SmartPay2)
- 版本格式：`SP2_V0.MMDDxx`（MM=月, DD=日, xx=版本序號）
- 範例：`SP2_V0.0813sd`

### 發布流程（依照 push-check-list.md）
1. 在小卡和娃娃機測試新功能
2. 更新 `analogCoinPay_Main.py` 第一行版本號
3. 檢查 sourceFiles 檔案差異
4. 複製檔案到 `releaseFiles/latestVersion`
5. 壓縮為 SP2_Vxxxxx.zip 備份
6. 更新 README.md 的 code-change list
7. Git commit 和 push

## OTA 更新機制

- 檢查 `otalist.dat` 檔案決定是否進行 OTA
- 從 GitHub repository `propsky/analogCoinPay` 分支 `SP2_HWv1` 下載更新
- 更新完成後自動重啟

## 狀態管理

系統使用狀態機模式，主要狀態包括：
- `NONE_WIFI`：未連接 WiFi
- `NONE_INTERNET`：已連接 WiFi，未連接網際網路
- `NONE_MQTT`：已連接網路，未連接 MQTT
- `STANDBY_MQTT`：正常運行狀態
- `GOING_TO_OTA`：準備進行 OTA 更新

## 開發注意事項

- 版本號務必在每次修改時更新 `analogCoinPay_Main.py` 第一行
- 所有 GPIO 操作需考慮硬體安全，避免意外啟動設備電源
- WiFi 斷線時系統仍需維持投幣器、電眼等基本功能
- 記憶體管理重要，適時使用 `gc.collect()`
- 電眼偵測需區分飛絡力電眼和通用型電眼的不同邏輯

## 檔案命名規範

- Python 模組：小寫加底線（如：`lcd_manager.py`）
- 版本備份：`SP2_V{版本號}.zip`
- 設定檔：`.dat` 副檔名（如：`wifi.dat`, `token.dat`）