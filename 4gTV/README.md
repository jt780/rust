# 📺 4GTV 串流代理 · 公开版

**4GTV 取流代理 + Web 管理面板 · 一键部署**

代理 TS / 转发 M3U8 / 302 重定向 | SOCKS5/HTTP 代理 | EPG · 在线播放器 

![arch](https://img.shields.io/badge/arch-amd64%20%7C%20arm64%20%7C%20armv7-blue)
![service](https://img.shields.io/badge/service-systemd-green)
![panel](https://img.shields.io/badge/panel-Web%20UI-orange)

---

## 🚀 安装

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/YanG-1989/rust/main/4gTV/4gtv.sh)
```

打开管理菜单，选 `1` 安装。装的时候会问两个问题，**全部回车走默认值也行**：

| 问题 | 默认 |
| --- | --- |
| 监听端口 | **随机**高位端口（约 10000–60000） |
| 隐藏路径 | **随机**生成（推荐保留） |

自动识别 CPU 架构（amd64 / arm64 / armv7），装到 `/opt/4gtv`，systemd 常驻 + 开机自启。

> **隐藏路径**：所有接口挂在随机前缀下（例如 `/a1b2c3d4`），不带前缀访问会 404，降低被端口扫描发现的概率。

装完二进制不会覆盖已有配置和频道数据，**更新版本直接再跑一次选 `1`** 即可。

## 🐳 Docker（amd64 自用版）

沿用 `IPTV Proxy` 的 Docker／Compose 目錄形式，直接包裝既有執行檔，不執行安裝腳本、不安裝 systemd，也不發布映像。**本 Docker 版本僅支援 `linux/amd64`，不建置或測試 ARM。** 建置時會核對二進位的固定 SHA-256；容器啟動時不會下載更新。

### 啟動

```bash
cd ~/projects/YanG-1989-rust/4gTV
cp -n .env.example .env
mkdir -p data
chmod 700 data
docker compose up -d --build
docker compose ps
```

- 本機 `ubuntu` 的 UID/GID 是 `1001:1001`，`.env.example` 已對應。換主機時先用 `id -u`、`id -g` 確認，再調整 `FOURGTV_UID`、`FOURGTV_GID`；`data` 必須由該 UID/GID 可寫。
- 請先建立 `data` 再啟動，避免 Docker 自動建立 root 擁有的 bind mount。容器不會以 root 自動修改主機資料的擁有者。
- 預設主機端 `127.0.0.1:18080` → 容器 `8080`，**不對外開放主機介面**。遠端瀏覽可使用 SSH tunnel，或下述 `cf-net`。
- 如需 LAN 存取，可把 `FOURGTV_BIND` 改成主機的 LAN IP；不要在沒有額外存取控制時任意綁 `0.0.0.0`。

### 路徑與管理密鑰

第一次啟動時，`BASE_PATH` 留空會產生隨機前綴，並保存在 `data/.docker-base-path`；重建容器不會更換它。可在自己的終端機讀取：

```bash
docker compose exec 4gtv cat /data/.docker-base-path
docker compose exec 4gtv cat /data/4gtv_admin_key.txt
```

請勿把管理密鑰、含密鑰的網址或完整設定貼到公開場所。若前綴為 `/你的前綴`：

- 首頁：`http://127.0.0.1:18080/你的前綴`（**沒有尾斜線**）。
- 播放器：`http://127.0.0.1:18080/你的前綴/player`。
- 管理頁：`http://127.0.0.1:18080/你的前綴/admin?key=你的管理密鑰`。
- 訂閱：`http://127.0.0.1:18080/你的前綴/4gtv.m3u`。

`BASE_PATH=off` 僅在第一次啟動時明確停用前綴，首頁即為 `/`。**隱藏路徑不是完整的存取控制**；不要因此裸露服務到公網。

### 設定與資料持久化

`./data` 掛載到容器 `/data`，保留整個目錄：

```text
data/
├── .docker-base-path      Docker 包裝保存的路徑（純文字，不執行）
├── 4gtv_admin_key.txt     程式產生的管理密鑰
├── 4gtv_config.json       程式／面板維護的設定
└── 其他頻道、快取等執行時資料
```

- `BASE_PATH` 是**第一次啟動的預設值**；已有 `.docker-base-path` 時以檔案為準。要改前綴，先停容器，備份後移除這個單一檔案、調整 `.env`，再啟動。舊的播放與訂閱網址會失效。
- `PORT` 每次啟動都會傳給程式；Compose 同時調整內部映射。`FOURGTV_PORT` 只改主機端埠，不影響容器內部埠。
- `4gtv_config.json` 與管理密鑰不會被 entrypoint 覆寫；其他設定使用面板修改。匯入舊資料時，要把原本的隱藏前綴設定到首次啟動的 `BASE_PATH`。
- 設定、密鑰與路徑檔使用 `0600`；啟動時也會收緊既有設定／密鑰權限。檔案需由容器的 UID/GID 擁有，不能使用 symlink。
- 一份資料目錄只供一個服務使用。備份前先停止容器，避免複製到寫入一半的資料。
- `.env`、`data/` 都被 Git 忽略；Docker build context 使用白名單，不包含設定、密鑰、文件或其他架構的執行檔。

### 使用既有 `cf-net`

```bash
docker network inspect cf-net >/dev/null
docker compose -f compose.yaml -f compose.cf-net.yaml up -d --build
```

容器會同時加入 Compose 預設網路與現有 `cf-net`。同網路的反向代理可連 `http://4gtv:8080`（若改 `PORT`，此處也要調整）；瀏覽器要求仍須帶正確的隱藏前綴。此檔案**不會建立或修改 Cloudflare Tunnel／DNS**。

僅走 Tunnel 時可移除 `compose.yaml` 的 `ports` 段落；`cf-net` 的容器間連線不受影響。若公開代理入口，應另加存取控制。應用程式若要連其他代理容器，請使用其 Docker DNS 名稱，不能把容器內的 `127.0.0.1` 當成主機。

### 管理、更新與驗證

```bash
docker compose logs -f 4gtv
docker compose restart 4gtv
docker compose down                     # 保留 ./data
docker compose up -d --build             # 使用目前本機的二進位重新建置
python3 -m unittest discover -s tests -p 'test_docker_*.py' -v
python3 tests/smoke_docker.py --skip-cf-net # 基本版，不需要 cf-net
python3 tests/smoke_docker.py              # 已有 cf-net 時，加測容器間連線
```

- 使用 cf-net 覆寫檔啟動時，後續 `up`／`down` 也使用相同的 `-f compose.yaml -f compose.cf-net.yaml` 組合。
- 上游二進位更新後，SHA-256 檢查會故意拒絕舊 pin；確認來源後更新 Dockerfile 的雜湊，再重建映像。
- 容器採非 root、唯讀 rootfs、`cap_drop: ALL`、`no-new-privileges`、`init: true`，不需要 privileged、host networking 或 TUN。
- Healthcheck 讀取持久化的隱藏路徑，不探測預期為 404 的裸根路徑，也不擅自加尾斜線。
- `init: true` 用於轉送停止訊號；SIGTERM 結束不代表程式提供完整的應用層 graceful flush。
- HTTP 頁面與 Docker 健康狀態通過，不等於上游頻道、帳號登入、EPG 或實際直播已驗證。這些依自身合法帳號及網路環境另測。

## 🎛️ 面板

装完后脚本会打印地址，形如：

```
http://服务器IP:<端口>/<隐藏路径>/admin?key=<管理密钥>
播放器：http://服务器IP:<端口>/<隐藏路径>/player
订阅：  http://服务器IP:<端口>/<隐藏路径>/4gtv.m3u
```

管理密钥在安装目录下的 `4gtv_admin_key.txt`（首次启动自动生成）。**请妥善保管，不要泄露。**

面板可配：播放模式、代理、登录凭证、EPG、频道更新、缓存清理等。

> 默认监听 `0.0.0.0`。**记得在防火墙 / 云安全组放行对应 TCP 端口。**

## 🧰 常用命令

| 命令 | 作用 |
| --- | --- |
| `bash 4gtv.sh` | 打开管理菜单 |
| `bash 4gtv.sh install` | 安装 / 更新 |
| `bash 4gtv.sh url` | 打印访问地址 |
| `bash 4gtv.sh port <N>` | 改监听端口 |
| `bash 4gtv.sh path </xxx>` | 改隐藏路径（`off` = 关闭） |
| `systemctl restart 4gtv` | 重启服务 |
| `journalctl -u 4gtv -f` | 看运行日志 |
| `bash 4gtv.sh uninstall` | 卸载 |

也可直接用环境变量启动：

```bash
PORT=12345 BASE_PATH=/mysecret /opt/4gtv/4gtv
```

## 📂 文件位置

```
/opt/4gtv/
├── 4gtv                 二进制
├── env                  端口 / 隐藏路径
├── 4gtv_admin_key.txt   管理面板密钥
├── 4gtv_config.json     配置
└── （频道映射、缓存等运行时文件）
```

卸载时会问要不要一起删 `/opt/4gtv`，选 `N` 就只停服务、保留数据，重装即恢复。

## ✨ 功能概览

| 功能 | 说明 |
| --- | --- |
| 模式1 · 代理 TS | 服务端反代切片，兼容性最好 |
| 模式2 · 转发 M3U8 | 改写列表，切片直连 CDN |
| 模式3 · 302 重定向 | 几乎零流量（需客户端能直连 CDN） |
| 代理 | SOCKS5 / SOCKS5h / HTTP，可分别用于 API 与 M3U8 |
| 登录模式 | 面板一键登录，解锁更高清 |
| EPG | 可选开启，定时更新 |
| API 限流 | **内置**，限制并发取流并带排队超时，降低封 IP 风险 |


## ℹ️ 说明

- **请勿将服务裸奔公网**或提供给不信任的第三方；仅供个人学习研究。
- 请勿对大量频道短时间并发刷取流。
- 想换下载源：`FOURGTV_PUBLIC_URL=https://你的地址/4gtv-linux-{arch} bash <(curl -fsSL ...)`

## 免责声明

本项目仅供个人学习与研究。因滥用导致的 IP 封禁、账号风险与法律责任由使用者自行承担。
