<div align="center">

# 🌊 MixFlow

**多协议代理 + Web 管理面板 · 一键部署**

Trojan · Hysteria2 · SOCKS5 / HTTP　|　直连 / WARP 出站　|　内核终极优化

![arch](https://img.shields.io/badge/arch-amd64%20%7C%20arm64-blue)
![systemd](https://img.shields.io/badge/service-systemd-green)
![panel](https://img.shields.io/badge/panel-Web%20UI-orange)

</div>

---

## 🚀 安装

推荐**全自动**一条龙 —— 全新机器直接跑这条，装好面板、建好节点、做完优化：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/YanG-1989/rust/main/MixFlow/mixflow.sh) oneclick
```

一个 `Y` 确认，全程无需其它输入。跑完屏幕直接给出**面板地址 + 账号密码 + 两条节点链接**：

> **①** `内核优化`[代理模式]　**②** 建 `Trojan-[地区]` 节点　**③** 建 `Hysteria2-[地区]` 节点 　**④** 建 `Socks5-[地区]` 节点 

<details>
<summary>只想装好、自己配置？（不带 <code>oneclick</code>）</summary>

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/YanG-1989/rust/main/MixFlow/mixflow.sh)
```

打开管理菜单，交互式设置面板端口 / 隐藏入口 / 密码，不自动建节点。之后随时按 `g` 再一键建节点。
</details>

两种方式都会自动识别 CPU 架构（amd64 / arm64），装到 `/opt/mixflow`，systemd 常驻 + 开机自启。

## 🐳 Docker

支援 `linux/amd64` 與 `linux/arm64`。映像建置時會選擇對應的二進位檔並驗證固定 SHA-256。

```bash
cd MixFlow
cp .env.example .env
# 編輯 .env，至少更改 MIXFLOW_PANEL_PASSWORD
docker compose up -d --build
```

面板預設為 `http://伺服器IP:12321/`。設定與節點資料保存在 `./data`；環境變數只在第一次產生 `data/config.toml` 時使用，容器重建不會覆寫既有設定。

Compose 預設提供 `/dev/net/tun`、`NET_ADMIN` 與 IPv4 forwarding，供 WARP 出站使用。主機必須存在 `/dev/net/tun`；若只使用 direct 出站，可移除 `devices`、`cap_add` 與 `sysctls`。

### 節點連接埠

MixFlow 由面板動態建立節點，因此 Docker 無法預先知道節點連接埠。新增節點後，請把相同連接埠加入 `compose.yaml` 的 `ports`，再重建容器：

```yaml
ports:
  - "12321:12321/tcp" # 面板
  - "443:443/tcp"     # Trojan / Mixed
  - "8443:8443/udp"   # Hysteria2
```

### 使用外部 `cf-net`

```bash
docker network inspect cf-net >/dev/null
docker compose -f compose.yaml -f compose.cf-net.yaml up -d --build
```

容器會同時加入 Compose 預設網路與既有 `cf-net`。同網路的 Cloudflare Tunnel 可使用 `http://mixflow:12321` 連線；若設定隱藏入口，網址須附加該路徑。只透過 Tunnel 使用面板時，可以移除面板的 `ports` 映射。

> `mixflow optimize` 會修改主機核心參數，不適合從容器執行；Docker 版只設定容器 namespace 需要的 forwarding。完整主機優化仍應在主機層進行。

## 🎛️ 面板

默认地址 `http://服务器IP:12321`，账号 `admin` / `admin123`（**请尽快改**）。

**隐藏入口**：设一个随机路径后，只有访问 `http://IP:12321/你的密路径` 才进得去，其它路径一律 404，扫端口的人看不到面板存在。

## 🧰 常用命令

> 装好后二进制已软链到 `PATH`，可全局使用 `mixflow`。改动重启服务生效。

| 命令 | 作用 |
| :-- | :-- |
| `mixflow.sh` | 打开管理菜单 |
| `mixflow.sh oneclick` | 一键建两个节点 + 终极优化 |
| `mixflow quicknode --tag HK` | 建 Trojan + Hysteria2（随机端口） |
| `mixflow optimize` | 终极代理模式内核优化 |
| `mixflow panel --port <N>` | 改面板端口 |
| `mixflow panel --path /xxx` | 设隐藏入口（`--path off` 关闭） |
| `mixflow panel --pass <密码>` | 改面板密码（忘密码也能改，不用进面板） |


---

<div align="center">
<sub>放行提醒：节点端口需在防火墙 / 云安全组开放 —— Trojan 走 <b>TCP</b>，Hysteria2 走 <b>UDP</b>。</sub>
</div>
