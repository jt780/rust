# 4GTV Docker 化可行性研究

> 歷史研究快照：後續已依使用者要求加入 amd64 自用 Docker 封裝，操作以 [README 的 Docker 章節](README.md) 為準。本文「尚未建立 Dockerfile／Compose」等敘述，是研究當下的狀態，不代表目前目錄。

## 結論

**可行，而且不必改寫 Rust 程式。** `4gtv.sh` 是安裝／管理外殼，真正的服務是架構對應的 `4gtv-linux-*` 執行檔。Docker 版本應直接啟動執行檔，讓 Compose 管理環境變數、資料掛載與重啟，而不是把互動安裝腳本或 systemd 搬進容器。[S1][S2]

這次已實際驗證 **Linux amd64 在 Alpine 3.21 容器內可啟動並提供 Web 頁面**，且不需要 root、額外 Linux capabilities 或主機網路模式。[E1]

**範圍：研究與隔離 smoke test，不是已完成的正式 Docker 發行版。** 沒有新增正式 Dockerfile／Compose，沒有部署長駐服務，沒有測試實際頻道播放、上游登入或付費內容，沒有公開推送映像。

## 研究版本與 Git 更新

- 使用者提供的字面路徑：`~/projects/YanG-1989/rust/4gTV/4gtv.sh`；本機沒有此目錄。
- 找到的實際 checkout：`/home/ubuntu/projects/YanG-1989-rust`。
- `origin`：`https://github.com/YanG-1989/rust.git`。
- 依使用者指示切換到 `main`，執行 `git pull --ff-only origin main`。
- 更新：`d302316` → `2fc790a9faba80b0cac68d4e8de2b68c5b500a98`，fast-forward，無 merge conflict。
- 研究依據固定在上述 commit；腳本自報版本 `1.1.1`，**不能據此推定二進位版本**。[S1]
- 原有 `feat/iptv-proxy-docker` 分支仍保留在 `7ed9264831c3082f0165da14c5c56507374ad34f`。
- 原有 `IPTV Proxy/.env` 與 `IPTV Proxy/data/` 未刪除、未讀取內容；切回上游 main 後，它們呈現為 untracked。後續若提交 Docker 檔案，應精確指定檔案，不能把它們一起加入 Git。

## 原始程式如何運作

- 腳本偵測 amd64／arm64／armv7，下載對應 ELF 到 `/opt/4gtv/4gtv`。[S1]
- systemd 的實際命令只是 `ExecStart=/opt/4gtv/4gtv`，工作目錄 `/opt/4gtv`；沒有必須透過安裝腳本才能啟動的步驟。[S1]
- 可用 `PORT`、`BASE_PATH` 環境變數直接啟動；README 說明預設監聽 `0.0.0.0`。[S2]
- 執行時在工作目錄產生 `4gtv_admin_key.txt`、`4gtv_config.json`，另有頻道資料與快取需要一併保存。[S2][E1]
- 原腳本的系統服務把 stdout/stderr 導向 null；不能只依 README 的 `journalctl` 範例承諾會有完整日誌。Docker 包裝應保留 stdout/stderr，同時確認程式自己的檔案日誌行為。[S1]
- 所檢查的 main checkout 只有發布執行檔、腳本與文件，沒有追蹤到 Rust `.rs`／Cargo 檔、Dockerfile、LICENSE 或 COPYING 檔。因此這是**封裝既有執行檔**，不是可從公開原始碼重建 Rust 程式的方案。[E2]

## 二進位檢查

`file` 對三個執行檔均辨識為靜態連結 ELF；amd64 的 `readelf -l/-d` 沒有 interpreter 或 dynamic section。[E2]

- `4gtv-linux-amd64`：x86-64。
  SHA-256：`a46ccfa3bd08cd06b3f41f411a1545981824aa405f69dff84fde8d7ac77a597e`
- `4gtv-linux-arm64`：ARM aarch64。
  SHA-256：`e2c514e8953563b26cd9722d2c709f28d3eb0483efa5bb1f26912f4454f7eea8`
- `4gtv-linux-armv7`：32-bit ARM EABI5。
  SHA-256：`738116a39266df994452229c534c9e4e4328187aed5e9e49248db50b58e5f50b`

這些檔案支持規劃 `linux/amd64`、`linux/arm64`、`linux/arm/v7` 的架構選擇；**目前只有 amd64 實際啟動驗證，ARM 不算已測通。** SHA-256 用於固定研究與包裝版本，不代表上游簽章或安全稽核。

## 實際容器驗證

成功測試觀察時間：`2026-09-14T16:51:30.040925+00:00`。[E1]

條件：

- Docker Engine `29.2.1`；Compose `v5.1.0`；主機 x86_64。[E2]
- 使用現有 `alpine:3.21`，image ID／RepoDigest：`sha256:48b0309ca019d89d40f670aa1bc06e426dc0931948452e8491e3d65087abc07d`。[E2]
- 二進位以唯讀 bind mount 提供，複製到容器內 tmpfs 再賦予執行權；**沒有修改 repo 內執行檔的 Git mode**。
- `--network none`、不 publish 主機連接埠、不傳入帳號憑證。
- UID/GID `65534:65534`、`--cap-drop ALL`、`no-new-privileges`、唯讀 rootfs，工作目錄與 `/tmp` 使用 tmpfs。
- `--init`，啟動前 `umask 077`。
- 測試值：`PORT=18080`、`BASE_PATH=/docker-research`。

HTTP 結果：

- `/` → **404**。
- `/docker-research` → **200**。
- `/docker-research/` → **404**；尾斜線不可擅自補上。
- `/docker-research/player` → **200**。
- `/docker-research/admin` → **200**。
- 加入容器本次生成的管理密鑰後，管理頁也回 **200**。密鑰未回顯或保存到研究檔。**僅憑頁面 200 不能判定管理 API 的驗證或權限隔離是否安全。**

檔案與程序結果：

- 自動生成 `4gtv_admin_key.txt` 與 `4gtv_config.json`。
- `umask 077` 下兩者權限均為 **600**；初次未收緊 umask 的測試為 **644**。正式 wrapper 應收緊 umask，且另外考慮既有資料的權限遷移。
- 直接把二進位當 PID 1 的前次測試，在 `docker stop --time 3` 後 exit **137**；加入 `--init` 的最終測試 exit **143**，不再需要超時後 SIGKILL。143 只代表 SIGTERM 終止，**未驗證應用層資料是否完整 flush**。
- 最終 `smoke_passed=true`；測試容器已移除且已讀回驗證。
- 探測程式前兩次的問題分別是 Docker local logging 選項（預設壓縮搭配 `max-file=1` 被拒絕），以及 wget 錯誤文字讓 HTTP 狀態被重複計數；修正後才採用上述成功結果，沒有把錯誤輸出當作成功。

## 建議的正式 Docker 設計

1. **Dockerfile：直接封裝執行檔。** 多階段依 `TARGETARCH`／`TARGETVARIANT` 選擇版本並驗證固定 SHA-256，runtime 只留下所選檔案；不要每次啟動都從浮動 `main` 下載。
2. **使用 exec 啟動，不執行 `4gtv.sh install`。** 不需要 systemd、OpenRC、sudo 或互動式選單。這也避開腳本的隨機主機連接埠與主機服務管理。
3. **獨立資料目錄。** 建議執行檔在 `/usr/local/bin/4gtv`，`WORKDIR /data`；掛載完整 `/data` 保存密鑰、設定、頻道與快取。正式版必須再驗證容器重建後仍使用同一份資料。
4. **Compose 設定明確化。** 以 `PORT` 設定固定容器內埠，例如 `8080`；主機埠由使用者設定。`BASE_PATH` 保留隱藏前綴，若自動生成需持久化，不能每次重建就更換。
5. **預設不裸露公網。** 綁定 loopback，或接既有反向代理的 Docker network；需要 LAN 使用時再明確調整。容器內 `127.0.0.1` 不是主機或其他代理容器，SOCKS5／HTTP 代理位址需相應調整。[S2]
6. **最低權限。** 非 root 執行、`init: true`、`umask 077`、capabilities 全移除。這次 Web smoke test 不需要 privileged、host networking、TUN 或 NET_ADMIN；其他可選功能仍需個別測試。
7. **Healthcheck 使用真正路徑。** 有 `BASE_PATH` 時探測 `http://127.0.0.1:${PORT}${BASE_PATH}`，不要探測根路徑，也不要自動附加尾斜線。正式 wrapper 應驗證 port 與 path 格式。
8. **日誌與更新。** 加上容器日誌輪替；更新靠重建映像並保留 volume。若使用 Docker `local` log driver，預設壓縮下避免 `max-file=1`。不在容器啟動時自行更新二進位。
9. **HTTPS 信任鏈待連網驗證。** 輕量 runtime 可包含 CA certificates，但本次離線測試不能證明 Rust 執行檔是否需要系統 CA、如何使用代理，或 CDN/TLS 全鏈路可用。

## 限制及未驗證項目

- **沒有實際播放驗證。** 首頁／播放器 HTML 回應正常，不等於頻道、EPG、登入、M3U8／TS 轉發或 302 直連可用。[S2]
- Docker 不會改變上游帳號授權、來源網路／地域條件或限流。這些需在合法、授權的使用環境中另測；不可把本次離線結果當作已能收看。
- ARM64／ARMv7 尚未建置及執行測試。
- 持久化 volume、重啟後密鑰不變、反向代理、代理連線及資料備份還沒實測。
- 上游根 README 將授權交由各目錄說明，但 4gTV README 只有個人學習／研究用途與免責聲明，未見明確允許重新散布的開源授權。自用研究包裝與**公開發布含二進位的映像**應分開處理；公開散布前先向作者確認授權。[S2][S3]

## 證據與第一方來源

- [S1] 固定 commit 的安裝腳本：<https://github.com/YanG-1989/rust/blob/2fc790a9faba80b0cac68d4e8de2b68c5b500a98/4gTV/4gtv.sh>。重點：L12–23 版本／路徑／下載，L140–159 systemd 工作目錄與命令，L230–249 密鑰，L253–289 安裝與前景啟動，L348–350 日誌。
- [S2] 同版本 4gTV README：<https://github.com/YanG-1989/rust/blob/2fc790a9faba80b0cac68d4e8de2b68c5b500a98/4gTV/README.md>。重點：L32–46 面板與監聽，L61–76 環境變數與檔案，L80–101 功能與使用限制。
- [S3] 根 README 授權說明：<https://github.com/YanG-1989/rust/blob/2fc790a9faba80b0cac68d4e8de2b68c5b500a98/README.md#license>。
- [E1] 本機實測程式 `/tmp/4gtv-docker-research/probe.py`；最終 JSON `/tmp/4gtv-docker-research/probe-result.json`。測試容器：`4gtv-research-1b203053a6`，ID `dc41f31ae53d6bddf401fe6359192822f848964dcac7a7ac5db5dac5c3e067ef`，已移除。
- [E2] 本次工具實際執行：`git status`／`git log`／`git ls-files`、`file`、`sha256sum`、`readelf -l/-d`、`bash -n 4gTV/4gtv.sh`、`docker version`／`docker info`／`docker compose version`／`docker image inspect`。相關核心結果已列於本報告；`/tmp` 內探測附件屬暫存，不保證長期保存。
