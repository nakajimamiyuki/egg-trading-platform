# 蛋品交易平台 Mac 部署运行方案（小白版）

适用人群：**没有任何开发经验的使用者**
目标：在你的 Mac 上把平台跑起来，浏览器能打开、能登录使用
全程约 **30 分钟**（其中 20 分钟是等下载和安装，真正操作只有几步）

---

## 准备清单

- 一台 Mac（近 5 年内的都可以，内存 8GB 以上，建议 16GB）
- 能上网
- 磁盘剩余空间 20GB 以上（左上角  → 关于本机 → 储存空间 可以查看）

---

## 第一步：安装 Docker Desktop（15 分钟）

Docker 是一个"软件集装箱"工具，平台所有部件都打包在里面，装上它就等于装好了全部环境。

1. 打开浏览器，访问官网下载页：
   **https://www.docker.com/products/docker-desktop/**
2. 点击 **Download for Mac** 按钮。
   - 如果问你选芯片：近年的 Mac 选 **Apple Chip**（M1/M2/M3/M4）；2020 年以前的老 Mac 选 **Intel Chip**
   - 不确定的话：点左上角  → 关于本机，看"芯片"一栏
3. 下载完成后，双击下载的 `Docker.dmg` 文件
4. 在弹出的窗口里，把 **Docker 图标拖进 Applications（应用程序）文件夹**
5. 打开"应用程序"文件夹，双击 **Docker** 启动
   - 第一次会提示"是否确定打开从网上下载的应用"→ 点**打开**
   - 可能会要求输入 Mac 开机密码授权，输入即可
   - 如果弹出协议页面，点 **Accept** 接受
6. 等待右上角菜单栏出现 🐳 小鲸鱼图标，等它不再动（约 1 分钟），说明 Docker 已就绪
7. **调大内存**（重要，不然后面会卡）：
   - 点菜单栏的 🐳 小鲸鱼 → **Settings**（齿轮图标）
   - 左侧选 **Resources**
   - 把 **Memory** 的滑块拖到 **6 GB** 以上（你内存够就拖到 8 GB）
   - 点右下角 **Apply & Restart**，等它重启完成

---

## 第二步：获取平台代码（5 分钟）

> 方法一最简单，不需要装任何东西。

### 方法一：网页下载压缩包（推荐小白）

1. 浏览器打开仓库地址（先确保你已登录自己的 GitHub 账号）：
   **https://github.com/nakajimamiyuki/egg-trading-platform**
2. 页面上方有个绿色按钮 **<> Code**，点它 → 选 **Download ZIP**
3. 下载后双击解压，得到一个文件夹 `egg-trading-platform-develop`（或类似名字）
4. **把它拖到桌面**，方便后面找
   - 建议顺手把文件夹改名为 `egg-platform`（短一点好输）

### 方法二：用 git 命令下载（适合以后还要更新代码的人）

需要先装 Git 和 GitHub 登录工具，略复杂，建议先按方法一跑通，以后需要再补。

---

## 第三步：启动平台（10 分钟，主要是等）

1. 打开"终端"：
   - 按键盘 **Command + 空格**，输入 `终端` 或 `Terminal`，按回车
2. 在终端里输入下面命令（注意 `cd` 后面有个空格），**先输 cd 不要回车**：

   ```
   cd 
   ```

   然后把桌面上那个代码文件夹（`egg-platform`）**用鼠标拖进终端窗口**，路径会自动填上，像这样：

   ```
   cd /Users/你的用户名/Desktop/egg-platform
   ```

   按回车。
3. 粘贴下面这条命令，按回车：

   ```
   docker compose up -d --build
   ```

4. 开始下载和安装，屏幕会滚动很多文字，**第一次需要 5–10 分钟**（取决于网速），耐心等到不再滚动、回到可输入状态
5. 验证是否启动成功，粘贴这条命令按回车：

   ```
   docker compose ps
   ```

   应该看到 6 行服务（egg-postgres、egg-redis、egg-rabbitmq、egg-minio、egg-backend、egg-frontend），状态都是 `Up` 或 `healthy`

---

## 第四步：打开平台（1 分钟）

1. 打开浏览器（Safari/Chrome 都可以），地址栏输入：

   **http://localhost:8080**

2. 看到"蛋品交易平台"登录页，说明部署成功 🎉
3. 用下面的账号登录体验：

   | 账号 | 密码 | 身份 |
   |---|---|---|
   | business01 | 123456 | 业务员（审批、建仓、定价） |
   | finance01 | 123456 | 财务（付款审批、发票、对账） |
   | farm001 | 123456 | 养殖户（仓库、产蛋、核销放行） |
   | buyer001 | 123456 | 采购商（商品大厅下单） |
   | admin | admin123 | 管理员（参数配置） |

4. （可选）想体验完整业务演示数据，在终端执行（同样先 `cd` 到代码文件夹）：

   ```
   bash scripts/demo_seed.sh
   ```

   会造出已入驻的养殖户、采购商、已建好并上架的交割仓，登录 buyer001 就能直接在"商品大厅"下单。

---

## 日常使用（以后每次怎么用）

平台数据是保存的，关机再开不会丢。

**每次开机后启动：**
1. 打开 Docker Desktop（等鲸鱼图标就绪）
2. 终端里 `cd` 到代码文件夹，执行 `docker compose up -d`
3. 浏览器打开 http://localhost:8080

**停止平台（不用时省资源）：**
```
docker compose down
```

**看运行状态：** `docker compose ps`
**出问题看日志：** `docker compose logs -f backend`（按 Control + C 退出）

**彻底重置（清空所有数据重新开始，谨慎）：**
```
docker compose down -v
docker compose up -d --build
bash scripts/demo_seed.sh
```

---

## 常见问题

**Q1：终端命令报错 `Cannot connect to the Docker daemon` 或 `docker: command not found`**
→ Docker Desktop 没启动。打开"应用程序"里的 Docker，等鲸鱼图标就绪后重试。

**Q2：浏览器打不开 http://localhost:8080**
→ 先执行 `docker compose ps` 看 6 个服务是否都在；不在就重新 `docker compose up -d`。再看看地址有没有输错（是 8080 不是 80）。

**Q3：第 3 步下载特别慢或卡住不动**
→ 国内网络访问 Docker 官方仓库慢。点 🐳 → Settings → Docker Engine，在配置里加一行镜像加速器（网上搜"Docker 国内镜像加速"，如中科大、网易的地址），保存重启后重试。

**Q4：提示端口被占用（port is already allocated）**
→ 你的 Mac 上其他软件占用了 8080 等端口。用文本编辑器打开代码文件夹里的 `docker-compose.yml`，把 `"8080:80"` 改成 `"8081:80"`，保存后重新 `docker compose up -d`，以后就用 http://localhost:8081 访问。

**Q5：点合同/文件的"查看"链接打不开**
→ 正常现象——这个链接只对部署本机有效。如果本机也打不开，在终端执行 `docker compose restart backend` 后再试。

**Q6：想给同一个办公室的同事演示**
→ 同事电脑浏览器输入 `http://你Mac的IP:8080`（你的 IP 在  → 系统设置 → 网络 里看，如 192.168.1.x）。同事的电脑和你的 Mac 要在同一个 Wi-Fi 下。

---

## 最后：一些说明

- 这套部署是**本地运行版**，所有数据都在你自己的 Mac 上，安全、免费，适合体验、演示、试用
- 真实对外营业（客户在外面访问、真实收付款）需要上云服务器，到时候看仓库里 `docs/开发计划/部署说明_Windows与Linux.md` 的上云章节
- 遇到问题先看第五部分 FAQ；解决不了，把终端里的报错截图发给技术人员
