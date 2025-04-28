# XT-Bot 🤖
**版本 1.0**

爬取Twitter推文和媒体，支持主页时间线/用户推文，通过Telegram Bot推送媒体内容

## 功能特性 🚀

- 定时同步Twitter主页时间线推文（30分钟/次）
- 同步指定用户全量历史推文及媒体（支持多用户）
- Telegram Bot自动推送图文/视频（支持格式限制：图片<10M，视频<50M）
- 本地化数据存储（推文数据/推送记录）
- GitHub Actions 自动化部署
- Twitter广播/空间链接推文同步到Telegram(飞书(可选))
- 操作异常告警信息添加飞书机器人消息通知(可选)

## 快速配置 ⚙️

### Secrets 配置项

在仓库 Settings → Secrets → Actions → Repository secrets 中添加：

```
AUTH_TOKEN    # X（Twitter）认证Token，从浏览器Cookie获取
SCREEN_NAME   # 你的X用户名，用于获取关注列表
BOT_TOKEN     # Telegram Bot Token（通过@BotFather创建机器人获取）
CHAT_ID       # Telegram用户ID（通过@userinfobot获取）
GH_TOKEN      # GitHub API Token
REDIS_CONFIG  # Redis配置(可选)格式如下：
{
  "host": "your.redis.host",
  "port": 6379,
  "password": "your_password",
  "db": 0
}
LARK_KEY      # 飞书机器人key(可选)https://open.feishu.cn/open-apis/bot/v2/hook/{LARK_KEY}
```

> 关于 REDIS_CONFIG 补充
>
> 1. 访问 https://app.redislabs.com/ 注册账号
> 2. 创建免费数据库（30M存储空间）
> 3. 存储运行相关配置，需手动添加key值【config】，对应项目的 config/config.json 文件中配置项

## 工作流程说明 ⚡

### 自动同步流程 [`XT-Bot.yml`]

- 🕒 每30分钟自动执行
- 同步最近24小时的主页时间线推文
- 过滤广告等非关注用户推文
- 支持相关参数配置请求
- 自动推送媒体到Telegram Bot

### 手动初始化流程 [`INI-XT-Bot.yml`]

同步指定用户全量推文（支持多用户） 在 config/config.json 中添加用户信息，执行相关流程操作

下面详细介绍一下可配置项（可通过redis的key键config来修改）

- interval: 请求间隔（默认5000ms）
- filterRetweets: 是否过滤转发推文（默认true）
- filterQuotes: 是否过滤引用推文（默认true）
- limit: 同步推文数量（默认不限制）
- screenName: 同步用户列表（例：同步@xxx时添加"xxx"）

示例如下

```json
{
  "interval": 5000,
  "filterRetweets": true,
  "filterQuotes": false,
  "limit": 2000,
  "screenName": [
    "xxx"
  ]
}
```

⚠️ **注意事项**

- 在同步指定用户全量推文流程前，请先在Actions面板停用XT-Bot.yml
- 或者使用`sh/`目录下`INI-XT-Bot.sh`(macOS)脚本执行相关流程操作，使用前需修改`REPO="your_username/XT-Bot"`

## 数据存储 🔒

```
├── Python/
│   └── output/      # Telegram推送记录
└── TypeScript/
    └── tweets/      # 推文原始数据存储
```

建议通过 [GitHub私有仓库](https://github.com/new/import) 导入项目保护隐私数据

## 技术参考 📚

- https://github.com/xiaoxiunique/x-kit
- https://github.com/fa0311/twitter-openapi-typescript

## 开源协议 📜

本项目基于 MIT License 开源

## 交流群 ✉️

https://t.me/+SYZQ5CO4oLE3ZjI1

## 自动获取和处理 Twitter/X 用户推文数据的工具。

## 功能特点

- 自动抓取指定用户的推文和媒体内容
- 获取用户关注列表
- 支持数据过滤（转推、引用等）
- 错误重试和恢复机制
- 支持 GitHub Actions 自动执行

## 环境要求

- Node.js 16+ 或 Bun 1.0+
- Python 3.10+
- Redis（可选）

## 快速开始

### 方法 1：使用安装脚本

```bash
# 克隆仓库
git clone https://github.com/your-username/XT-Bot.git
cd XT-Bot

# 运行安装脚本
chmod +x setup.sh
./setup.sh
```

### 方法 2：手动设置

```bash
# 克隆仓库
git clone https://github.com/your-username/XT-Bot.git
cd XT-Bot

# 创建必要的目录
mkdir -p Python/{dataBase,downloads,logs,output}
mkdir -p TypeScript/{data,logs,resp,tweets}
mkdir -p config

# 安装 TypeScript 依赖
cd TypeScript
bun install
cd ..

# 安装 Python 依赖
cd Python
pip install -r requirements.txt
cd ..

# 创建配置文件
echo '{
  "screenName": ["你的Twitter用户名"],
  "interval": 5000,
  "filterRetweets": true,
  "filterQuotes": true,
  "maxRetries": 3
}' > config/config.json
```

## 环境变量配置

在运行程序前，需要设置以下环境变量：

- `AUTH_TOKEN`: Twitter API 认证令牌
- `SCREEN_NAME`: 要抓取的 Twitter 用户名
- `REDIS_CONFIG`（可选）: Redis 配置信息，JSON 格式

### 设置环境变量示例

```bash
# Linux/macOS
export AUTH_TOKEN="你的认证令牌"
export SCREEN_NAME="你要抓取的用户名"

# Windows
set AUTH_TOKEN=你的认证令牌
set SCREEN_NAME=你要抓取的用户名
```

## 使用方法

### 获取用户推文和媒体

```bash
cd TypeScript/scripts
bun run fetch-tweets-media.ts
```

### 获取用户关注列表

```bash
cd TypeScript/scripts
bun run fetch-following.ts
```

### 运行 Python 处理脚本

```bash
cd Python/src
python INI-XT-Bot.py
```

## GitHub Actions 自动化

本项目支持通过 GitHub Actions 自动执行数据获取和处理流程。使用步骤：

1. Fork 本仓库
2. 在仓库设置中添加以下 Secrets:
   - `GH_TOKEN`: GitHub 个人访问令牌
   - `AUTH_TOKEN`: Twitter API 认证令牌
   - `SCREEN_NAME`: 要抓取的 Twitter 用户名
   - `LARK_KEY` 等其他可选配置（如需使用飞书通知）
3. 手动触发 "INI-XT-Bot" 工作流或设置定时触发

## 文件结构

```
XT-Bot/
├── .github/workflows/  # GitHub Actions 工作流配置
├── Python/             # Python 代码
│   ├── src/            # 源代码
│   ├── utils/          # 工具函数
│   ├── dataBase/       # 数据库文件
│   ├── logs/           # 日志文件
│   └── output/         # 输出文件
├── TypeScript/         # TypeScript 代码
│   ├── scripts/        # 脚本文件
│   ├── utils/          # 工具函数
│   ├── data/           # 处理后的数据
│   ├── logs/           # 日志文件
│   ├── resp/           # API 响应数据
│   └── tweets/         # 处理后的推文数据
└── config/             # 配置文件
```

## 错误处理

如果遇到 API 调用失败或其他错误，程序会自动重试，并在控制台输出详细错误信息。常见错误：

- `No data`: Twitter API 未返回数据，可能是认证令牌过期或用户不存在
- `API请求失败`: 网络连接问题或 API 限流
- `未设置环境变量`: 缺少必要的环境变量配置

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进本项目。提交前请确保代码符合项目的代码风格和测试要求。