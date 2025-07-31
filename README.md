# code-change list

**2025/7/31_SP2_V0.0731sa, Thomas**
1. 新增push check list(./push-check-list.md)
2. Eyes_IRDIS新增進中斷，紀錄正緣和負緣的時間點，Is_FEILOLI_eyes改到此中斷進行判斷和修改
3. Eyes_IROUT中斷後，不判斷Eyes_IRDIS、不修改Is_FEILOLI_eyes；飛絡力電眼的部分，新增判斷Eyes_Enable_time(IRDIS正緣->IROUT負緣)時間要大於500ms
4. 為了防只同樣的準位下，出現非預期的重複中斷。PAYOUT、Coin_IN1、Coin_IN2新增last_value，各自中斷時，會先判斷新值和舊值有沒有改變，若有才會做後續中斷處理。
5. 2和4的狀態再開機時會先讀取和修改，並且列印出log。
6. 刪掉多餘的空白和註解掉用不到的程式碼。
* Based on smartpay2 7/15_SP2_V0.0610sd, Thomas整理Sam修改
---
**2025/7/15_SP2_V0.0610sd, Thomas整理Sam修改**
1. 補上Sam的修改紀錄
a. Sam上傳了ntptime.py
b. Sam更新了senko.py
* Based on smartpay2 2025/6/10_SP2_V0.0610sb, Thomas
---
**2025/6/10_SP2_V0.0610sb, Thomas**
1. MQTT收到OTA指令時，在重開機以前會先關掉卡機電源和刷卡功能，以及關掉投幣器電源
* Based on smartpay2 2025/6/10_SP2_V0.0610sa, Thomas
---
**2025/6/10_SP2_V0.0610sa, Thomas**
1. wifi斷線時，不影響投幣器、卡機、電眼的相關功能，並且仍能定期清除WDT
2. 新增meter功能
3. 可以接受MQTT的epays、freeplays的啟動指令
4. 簡化MQTT publish重複的程式碼
5. 調整如果MQTT傳送失敗，就把狀態打回Wi-Fi斷線
6. 新增娃娃機故障偵測與對應處理GPIO設定的副程式
7. LCD導入Sui的新LCD模組py檔
8. 判斷電眼enable訊號，若曾經有enable就是飛絡力電眼，出獎判斷Low寬度；
	否則就是通用型電眼，出獎判斷Hi寬度
9. 為了等待中華4G用的TPLINK基地台開機，main.py連wifi以前會delay 60秒
	=> 此為短期解法會造成開機很久，應當找時間修正成長期解法
10. main.py會關掉卡機電源、投幣器電源、EPAY_EN
* Based on smartpay2 2025/5/5_SP2_V0.0505a, Thomas
---
**2025/5/5_SP2_V0.0505a, Thomas**
1. 完成投幣器、卡機傳給娃娃機的投幣訊號串接
* Based on smartpay2 2025/3/5_SP2_V0.01a, Thomas
---
**2025/3/5_SP2_V0.01a, Thomas**
1. 以智付小卡硬體V1.0開發，刪除smartpay1 SPHP_V1.00c的FEILOLI UART
2. MQTT暫時可以上傳了，但還有許多未修改確認部分，可能有BUG
* Based on smartpay1 2025/3/5_SPHP_V1.00c, Thomas
---

# to-be-do list
1. 整合SPHP_HWv1(開心小卡B1)的檔案，除了acp_m.py以外的4個py檔，檢查差異是否都同步導入
a. BN165DKBDriver.py => ok
b. senko.py => ok
c. wifimgr.py => 雖然已導入，但未確認功能差異
d. main.py => 雖然已導入，但未確認功能差異，並且有新版需要再排入更新
2. 繼續導入Sam20250505
3. 確認OTA是否正常
4. 修補小卡的重連機制，不嘗試連線時，想要完全關掉wifi模組
5. 針對飛絡力電眼enable/disable變化時，重新判斷出獎訊號時間
6. 確認OTA以下更新方式是否正常合理
a. 舊->新
b. 新->新
7. 正緣和負緣中斷，改成真的會依造以前準位狀態來判定是否真的有準位轉換