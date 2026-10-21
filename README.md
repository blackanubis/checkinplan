# checkinplan · 一年级学习打卡页

一个纯静态页面（nginx 容器托管）：**周计划打卡 + 打卡日历 + 语文/数学练习生成器**。
无后端、无数据库、不联网。打卡记录、RAZ 进度、错题本都存在浏览器 `localStorage` 里。

仓库：https://github.com/blackanubis/checkinplan

## 目录结构

```
.
├── docker-compose.yml          # 端口与持久化目录都用变量，部署时可改
├── nginx.conf                  # utf-8 + html 不缓存
├── .env.example                # 复制成 .env 后按需修改
├── make_icons.py               # 生成 favicon（页面已内联图标，此脚本仅供重新生成）
└── html/
    ├── index.html                  # 首页导航（两个入口）
    ├── 学习周计划与每日打卡.html     # 打卡日历 + 每日打卡 + 12 周计划（内含练习生成器视图）
    └── 语文数学练习生成器.html       # 出题 + 判分 + 错题本（独立页）
```

## 部署（Docker Compose）

默认端口 **13003**，页面目录默认用仓库里的 `./html`，两者都能在部署时改：

```bash
git clone https://github.com/blackanubis/checkinplan.git
cd checkinplan
cp .env.example .env     # 可选：改 WEB_PORT / APP_DIR
sudo docker compose up -d
# 访问 http://<NAS的IP>:13003
```

想让页面文件落到自己的目录（比如放到 docker 数据盘方便备份）：

```bash
APP_DIR=/vol1/1000/docker/checkinplan/html
mkdir -p "$APP_DIR" && cp -r html/. "$APP_DIR/"
echo "WEB_PORT=13003" > .env && echo "APP_DIR=$APP_DIR" >> .env
sudo docker compose up -d
```

> `APP_DIR` 指向的目录必须先存在且有内容，容器只是挂载、不会帮你生成初始文件。

## 更新页面

- 换 HTML：把新文件覆盖到 `APP_DIR`（或仓库 `html/`）即可，**不用重启**——nginx 直接读文件，且已配 `no-store`。
- 改了 `docker-compose.yml` / `nginx.conf` / `.env`：执行 `sudo docker compose up -d --force-recreate`。
- 直接拉新版：`git pull && sudo docker compose up -d`（若用了自定义 `APP_DIR`，记得重新 `cp -r html/. "$APP_DIR/"`）。

## 备份

要备份的只有一处：`APP_DIR` 指向的目录（页面文件）。
打卡/错题数据不在服务端，在浏览器里；换设备或清缓存会丢，重要进度建议顺手截图留档。

## 几点说明

- **中文文件名**：nginx 已配 `charset utf-8`，地址栏显示成 `%E5%AD%A6...` 是正常现象。
- **打印**：用系统浏览器（Chrome / Edge）打开再打印，不要在资料库/内嵌预览里点打印——内嵌环境会拦截打印调用。
- **图标**：favicon 已内联在 HTML 里（日历 / 对勾），页签和"添加到主屏幕"都有效；要换图标跑 `python make_icons.py` 重新生成并覆盖进 HTML。
- **计划起点**：第 1 周从 2026-10-26（周一）起，之前几天页面顶部会显示"适应与调整期"橙色卡片。
