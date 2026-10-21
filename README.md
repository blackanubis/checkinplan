# checkinplan · 一年级学习打卡页

单容器（**静态页面 + 数据同步 API**）：周计划打卡、打卡日历、语文/数学练习生成器，
打卡记录、RAZ 进度、错题本会同步到容器里的 SQLite，**换浏览器 / 换设备访问同一个地址就是同一份数据**。

仓库：https://github.com/blackanubis/checkinplan　镜像：`ghcr.io/blackanubis/checkinplan:latest`

## 结构

```
Dockerfile                 单容器镜像（python:3.12-alpine，页面 + API 一起打包）
server/app.py              Python 标准库写的静态服务 + /api/state（SQLite）
html/index.html            首页导航
html/学习周计划与每日打卡.html  打卡日历 + 每日打卡 + 12 周计划（内含练习生成器视图）
html/语文数学练习生成器.html    出题 + 判分 + 错题本（独立页）
docker-compose.yml         端口、数据目录都用变量
docker-compose.feiniu.yml  飞牛 NAS 直接粘贴版（绝对路径）
.github/workflows/ghcr.yml 推 main 自动构建多架构镜像推到 GHCR
```

## 部署

```bash
git clone https://github.com/blackanubis/checkinplan.git
cd checkinplan
cp .env.example .env      # 可选：改 WEB_PORT / DATA_DIR
sudo docker compose up -d
# 访问 http://<主机IP>:13003
```

飞牛 NAS（端口 13003、数据放 `/vol3/1000/project/cheackinplan/data`）：

```bash
sudo docker compose -f docker-compose.feiniu.yml up -d
```

## 数据怎么存的

- 页面先写浏览器 `localStorage`（秒开、离线可用），约 0.6 秒后整体快照 POST 到 `/api/state`。
- 服务端按 key 存进 `/data/state.db`（SQLite），带时间戳；打开页面时先拉服务端，服务端更新就覆盖本地并刷新一次。
- **连不上 API 时静默降级为纯本地存储**（用 file:// 打开、资料库内嵌预览、或拿纯 nginx 托管页面都属于这种情况）。
- 同步的 key：`check_YYYY-MM-DD`（每日打卡）、`cnma_wrongbook_v1`（错题本）、`raz_aa_count`、`weekdone`、`movies`。
- 多设备要共享，必须访问**同一个地址**（协议+域名+端口一致）；端口不同也算两份数据。
- 备份 = 复制 `state.db`（建议先停容器再复制，或直接复制也行）。

## 更新

页面或后端改完推到 `main` → Actions 自动构建 `linux/amd64` + `linux/arm64` 镜像并推 GHCR（约 3-5 分钟）。

```bash
sudo docker compose pull && sudo docker compose up -d
```

## 本地开发 / 不用 Docker

```bash
CP_WWW=./html CP_DATA=./data CP_PORT=13003 python server/app.py
```

## 说明

- 计划第 1 周从 **2026-10-26（周一）** 起，之前几天页面显示"适应与调整期"橙色卡片。
- 打印请用系统浏览器（Chrome / Edge）打开，不要在资料库/内嵌预览里点打印。
- favicon 已内联在 HTML 里；要换图标跑 `python make_icons.py` 重新生成。
