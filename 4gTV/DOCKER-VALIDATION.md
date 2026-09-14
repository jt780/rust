# Docker 驗證紀錄（amd64 自用版）

- 平台：`linux/amd64`；未建置或測試 ARM。
- 最終整合測試時間（UTC）：`2026-09-14T17:28:34.036770+00:00`。
- 本機映像：`4gtv:local`。
- 映像 ID：`sha256:a00c62037a5935238b258998a31ab3908da784ababb3b5765e9f3d6fb11569af`。
- 二進位 SHA-256：`a46ccfa3bd08cd06b3f41f411a1545981824aa405f69dff84fde8d7ac77a597e`。
- 原二進位與 `4gtv.sh` 未修改；映像與 Git 均不公開發布。

## 驗證結果

**29 項 unittest、30 項實際容器檢查全部通過。**

- Docker Compose 原生建置成功；映像內是已核對雜湊的 amd64 執行檔。
- 基本版與 cf-net 版均達 `healthy`；首頁、播放器、管理頁 HTTP 200。
- 非 root、唯讀 rootfs、capabilities 全移除、no-new-privileges、init 均讀回確認。
- 主機埠僅綁 `127.0.0.1`；未帶前綴的根路徑及錯加尾斜線按預期回 404。
- 強制重建容器後，路徑、管理密鑰、JSON 設定與測試資料逐檔雜湊一致。
- 既有路徑優先；即使未再採用的首次環境預設值格式錯誤，重建仍正常。
- 設定、密鑰與路徑檔均 `0600`；停止 exit `143`，未超時強制 SIGKILL。
- cf-net 保留 default 網路，且第二個容器能用 `4gtv:8080` 加隱藏前綴連線。
- 測試容器、臨時網路與資料已清除並讀回確認；既有 `cf-net` 保留。

## 審查處理

- **Standards**：無阻擋問題；首次預設驗證順序的非阻擋問題已修正，先重現失敗、再補 unit 與實際容器重建回歸測試。
- **Spec**：無阻擋問題；README 已分開基本版 `--skip-cf-net` 與選配網路完整測試，避免沒有 cf-net 的使用者無法執行基本驗證。
- 測試 harness 曾加入 `internal: true`，Docker 29 因而不建立主機 port binding；以最小對照測試確認後，移除測試用覆寫。正式 Compose 原本沒有此設定，上列結果來自正式網路設定。

## 重跑

```bash
python3 -m unittest discover -s tests -p 'test_docker_*.py' -v
python3 tests/smoke_docker.py --skip-cf-net
# 已有 cf-net 時，完整驗證：
python3 tests/smoke_docker.py --report /tmp/4gtv-docker-validation.json
```

煙霧測試使用獨立 Compose project 與臨時資料，不讀取使用者的 `.env`／`data`，結束清理自身資源。預設重建本機映像；已建置可加 `--skip-build`。

## 界線

沒有啟動長駐服務。本機映像、`.env` 與可寫 `data` 已備妥，啟動方式見 README。

沒有實際頻道播放、上游帳號登入、EPG 或串流完整驗證；HTTP 頁面可用不代表所有上游內容可用。SIGTERM 退出也不等於應用程式承諾 graceful flush，備份前仍應先停止容器。

紀錄僅對上述映像／二進位有效；更新後需重新驗證。
