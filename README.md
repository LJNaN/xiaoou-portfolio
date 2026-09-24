# xiaoou-portfolio

欧阳晓丽（平面设计师）的简历 + 作品集，形态是一个**只做竖向滚动的微信小程序**，
图片和文案都由后端接口提供。

## 为什么要拆成两半

19 张原图合计约 19 MB。直接打进小程序包体积会超标，而且**改一张图就得重新提交发版**。
所以：

- **小程序**只做展示层（包体只有几十 KB），启动时从接口拿清单、按需加载图片；
- **后端**（FastAPI + Pillow）负责发清单和图片，并把原图压成 750px 缩略图。

长流里加载的是缩略图（全页约 1 MB），点开才用 `wx.previewImage` 拉原图。
于是「换图不用发版」和「滚动不卡」同时成立。

## 目录

```
miniprogram/          小程序源码（不进服务器，只在本地/开发者工具里用）
  config/index.js     全项目唯一要改地址的地方（dev / prod）
  utils/api.js        取内容：先读缓存渲染，再后台刷新（stale-while-revalidate）
  pages/index/        唯一的页面：单页竖向长流
server/
  app/                FastAPI：content 清单 + 原图 + 惰性生成缩略图
  content/            简历与画册清单（进 git，改这里就能改线上文案）
  images/full/        19 张原图 —— **不进 git**，服务器上那份是唯一一份
  images/thumb/       缩略图缓存 —— 不进 git，服务端自动生成
tools/upload-images.sh  把本机原图 rsync 到服务器（CI 不管图）
docker-compose.yml    后端容器，挂进 gateway 的外部网络 web，别名 xiaoou-api
.github/workflows/    push main → rsync → docker compose up -d --build
```

## 数据流

```
小程序 ──https──▶ gateway(nginx) ──▶ xiaoou-api:5003 ──▶ /data/content/*.json
                                                          /data/images/{full,thumb}
```

网关那两段路由写在 `gateway` 仓库的 `routes.inc` 里（`/portfolio-api/`、`/portfolio-images/`），
不由本仓库管理。**接口路径前缀在三处必须一致**：`routes.inc`、`server/app/config.py`
的 `API_PREFIX` / `IMAGE_PREFIX`、`miniprogram/config/index.js` 的 `API` / `IMG`。

## 本地开发

后端：

```bash
cd server
pip install -r requirements.txt
IMAGES_DIR=./images CONTENT_DIR=./content uvicorn app.main:app --port 5003
curl -s http://127.0.0.1:5003/portfolio-api/health
```

微信开发者工具打开 **`miniprogram/`** 目录（不是仓库根目录），把
`config/index.js` 的 `ENV` 改成 `'dev'`，并在「详情 → 本地设置」里勾上
**不校验合法域名**。真机预览时勾这个没用，必须走线上域名。

## 部署

CI 在 push `main` 后自动跑：rsync 到 `/app/xiaoou-portfolio` →
`docker compose up -d --build`。用同一套 secrets（`SERVER_SSH_KEY` / `SERVER_HOST` / `SERVER_USER`）。

### 首次部署（顺序不能反）

**第 0 步必须手动做，否则接口正常但图片全 404：**

```bash
SERVER_USER=root SERVER_HOST=<服务器IP> sh tools/upload-images.sh
```

1. 服务器上先 `docker network create web`（gateway 那套已经有了）；
2. 本仓库 push `main`，等 CI 把后端拉起来；
3. 在服务器上自查：`curl -s http://127.0.0.1:5003/portfolio-api/health`；
4. `gateway` 仓库的 `routes.inc` 加上那两段 `location`（已加好）后 push。
   网关重建会**让弦集 / 对话 / 文稿 / 作品集四条路径各抖约 1 秒**。

### 日常改动

| 想改什么 | 怎么做 |
|---|---|
| 文案、联系方式、作品标题 | 改 `server/content/*.json` → push `main`（**不用传图、不用重建镜像**：容器每次请求都重读 JSON） |
| 换 / 加一张作品图 | 见下 |
| 改样式、交互 | 改 `miniprogram/` → 开发者工具上传新版本 → 提交审核发版 |

### 加一张新作品图（两步）

1. 把原图丢进 `server/images/full/`，在 `server/content/gallery.json` 里加一条
   （照抄邻页：`file` / `role` / `title` / `note` / `category`，`category` 留空就归到上一章）；
2. `sh tools/upload-images.sh`，然后 push `main`。

缩略图不用管，后端第一次被请求到会自动生成并落盘。图片 URL 上的内容版本号 `?v=` 由
内容 JSON + 图片大小/时间算出来，所以换图后小程序会自动拿到新 URL，不会看到旧图。

## 备份

**`/app/xiaoou-portfolio/server/images/full/` 是整个项目唯一不可再生的数据**
（原图不在 git 里，服务器上被删就没了）。文案和代码都在 git 里，随时能重建。

```bash
tar czf /root/migrate/xiaoou-images.tgz -C /app/xiaoou-portfolio server/images/full
# 也建议在本地留一份原图完整副本
```

正因如此，`.github/workflows/deploy.yml` 里的 rsync **必须带 `--exclude='server/images'`**：
rsync 不会删除被 exclude 的路径，一旦漏写，下一次部署的 `--delete` 会把服务器上的原图全部删掉。

## 还没做的（需要你提供）

- **域名 ICP 备案**：`www.jnnnn.top` 备案没下来之前，**真机一定连不上** ——
  阿里云会按 SNI 把带域名的连接直接重置（`ERR_CONNECTION_RESET`），
  `http://` 则返回 `Non-compliance ICP Filing` 的 403 页。这不是代码问题：
  同一个 IP 不带 SNI 访问端口 443 是 200。备案通过后无需改任何代码。
  等待期间真机调试把 `config/index.js` 的 `ENV` 改成 `'ip'`（裸 IP 直连）并勾「不校验合法域名」。
- **服务器域名白名单**：小程序后台「开发 → 开发设置 → 服务器域名」，
  把 `https://www.jnnnn.top` 加进 **request 合法域名** 和 **downloadFile 合法域名**
  （后者是「保存到相册」要用的）。白名单是精确匹配，`www.` 不能省也不能多。
- **微信号名片**：按你的要求先不做了，页面上只留一个「复制微信」按钮。

## 排错

- **接口通了、图全 404** → `server/images/full/` 是空的，跑 `tools/upload-images.sh`。
- **域名下 502** → 后端容器没起，或它没接进 `web` 网络 / 别名不是 `xiaoou-api`
  （`docker exec <网关容器> getent hosts xiaoou-api`）。
- **改了 routes.inc 或 nginx.conf 却不生效** → 网关配置是单文件 bind mount，
  绑的是 inode；rsync 是「写临时文件再改名」，`up -d` 不会重建，要 `--force-recreate`。
- **滚动时图片位置跳动** → 每张图的高度是按原图宽高比预留在 WXML 的
  `style="height:{{boxH}}rpx"` 上的。后端拿不到宽高时会退回 16:9 兜底，
  检查原图是不是损坏。
