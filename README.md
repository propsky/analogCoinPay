# code-change list

**2025/6/10_SP2_V0.0610sb, Thomas**
1. MQTT收到OTA指令時，在重開機以前會先關掉卡機電源和刷卡功能，以及關掉投幣器電源
* Based on smartpay2 2025/6/10_SP2_V0.0610sa, Thomas
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