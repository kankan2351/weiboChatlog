# CocoonChat

CocoonChat 是一个面向微博群聊的智能助手，既能 7×24 小时守护群聊，也支持在命令行中与您持续对话。项目内置消息持久化、上下文管理、自动回复、日志采集等能力，可用于快速搭建面向微博社区的自动化助手。

## 核心能力
- **微博群聊监控与自动回复**：接入指定群聊，轮询消息，识别 @ 机器人请求并通过大模型生成回复。
- **命令行对话模式**：直接在终端中与机器人交流，保留上下文，适合调试和灰度测试。
- **持久化与检索**：消息会同时写入 SQLite、Chroma 向量库以及处理记录文件，方便后续分析与问答。
- **自动化运维支持**：日志、数据库、Cookies 均可持久化到宿主机目录；提供 Docker 化方案支持快速部署与一键重启。

## 依赖要求
| 组件 | 说明 |
| --- | --- |
| Python | 3.8 及以上版本 |
| 浏览器 | Chrome / Chromium，与 Chromedriver 版本匹配 |
| 数据库 | 内置 SQLite3；无需额外安装服务器 |
| 大模型接口 | OpenAI / Azure OpenAI / DeepSeek 等兼容 OpenAI 协议的接口 |

> 💡 项目通过 `.env` 文件读取敏感配置，`Config` 类会在启动时校验必填项并自动创建 `data`、`logs` 等目录。

## 目录结构
```
chatbot/
├── main.py                # 入口脚本，支持 CLI 和 monitor 两种模式
├── weibo/monitor.py       # 微博群监控与 Selenium 登录流程
├── handlers/              # AI 回复、消息处理逻辑
├── db/sqlite_db.py        # SQLite 数据访问层
├── utils/config.py        # 配置解析与目录初始化
└── ...
```

## 部署方式
### 方式一：本地/服务器手动部署
1. **克隆代码库**
   ```bash
   git clone https://github.com/kankan2351/weiboChatlog.git
   cd weiboChatlog
   ```
2. **准备 Python 环境**（推荐使用虚拟环境）
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows 使用 .venv\\Scripts\\activate
   pip install --upgrade pip
   pip install -e .
   ```
3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 按需填写 OPENAI / AZURE / DEEPSEEK / WEIBO 相关参数
   ```
4. **安装 Chrome 与 Chromedriver**：确保两者版本一致；Linux 可以通过包管理器安装 `chromium` 与 `chromium-driver`。
5. **首次运行并登录微博**
   ```bash
   python -m chatbot.main --monitor
   ```
   终端会唤起浏览器窗口，手动完成登录后，Cookies 会缓存到 `./data` 目录。

### 方式二：Docker 化部署
项目提供多阶段 `Dockerfile` 与 `docker-compose.yml`，用于快速构建镜像并持久化运行数据。

1. **准备持久化目录**（只需执行一次）
   ```bash
   mkdir -p data logs persist/chroma_db persist/cookies
   ```
2. **复制并填写配置**
   ```bash
   cp .env.example .env
   # 编辑 .env，确保配置齐全
   ```
3. **构建镜像**
   ```bash
   docker compose build
   ```
4. **处理首次登录**（必须选择以下策略之一，获取可复用的微博 Cookies）
   - **策略 A：本地 GUI 登录后上传 Cookies**
     1. 在本地（有图形界面）执行：
        ```bash
        xhost +local:docker  # 允许容器访问本地显示
        docker compose run --rm \
          -e RUN_HEADFUL=true \
          -e DISPLAY=$DISPLAY \
          -v /tmp/.X11-unix:/tmp/.X11-unix \
          monitor python docker/save_cookies.py
        ```
     2. 在弹出的 Chromium 窗口中登录微博，成功后 `persist/cookies/weibo_cookies.json` 会生成。
     3. 将该文件安全地上传到服务器 `persist/cookies/` 目录。
   - **策略 B：服务器端一次性 VNC 登录**
     1. 在服务器上运行：
        ```bash
        docker compose run --rm -p 5901:5901 -e RUN_HEADFUL=true monitor \
          bash -lc '\
            Xvfb :99 -screen 0 1920x1080x24 & \
            fluxbox -display :99 & \
            x11vnc -display :99 -forever -shared -rfbport 5901 -nopw & \
            DISPLAY=:99 python docker/save_cookies.py \
          '
        ```
     2. 使用 VNC 客户端连接 `服务器IP:5901`，完成微博登录。
     3. 登录成功后退出容器，Cookies 会保留在共享卷 `persist/cookies/`。
5. **启动服务**
   ```bash
   # 监控模式常驻后台运行
   docker compose up -d monitor

   # 按需开启 CLI 会话（使用 profile，退出后容器即销毁）
   docker compose run --rm --profile cli cli
   ```
6. **查看运行状态**
   ```bash
   docker compose logs -f monitor
   ```

> `docker-compose.yml` 默认挂载以下卷：
> - `./data -> /app/data`
> - `./logs -> /app/logs`
> - `./persist/chroma_db -> /app/chroma_db`
> - `./persist/cookies -> /app/cookies`
> 
> 并通过 `.env` 注入所需环境变量，敏感信息不会硬编码进镜像。

## 使用指南
### 1. 命令行模式
- 本地运行：
  ```bash
  python -m chatbot.main
  ```
- Docker 环境：
  ```bash
  docker compose run --rm --profile cli cli
  ```
  在 CLI 中输入内容即可与机器人对话，输入 `quit` 退出。

### 2. 微博监控模式
- 本地运行：
  ```bash
  python -m chatbot.main --monitor
  ```
- Docker 环境：
  ```bash
  docker compose up -d monitor
  docker compose logs -f monitor
  ```
  日志中出现“polling new messages”或 AI 回复内容，即表示监控已生效。

### 3. 数据位置
| 数据类型 | 默认路径 |
| --- | --- |
| 处理过的消息 ID | `./data/processed_messages.json` |
| Chroma 向量库 | `./persist/chroma_db/` |
| SQLite 数据库 | `./data/chatbot.db` |
| 日志文件 | `./logs/` |
| 微博 Cookies | `./persist/cookies/weibo_cookies.json` |

### 4. 常用运维操作
- **重启监控**：`docker compose restart monitor`
- **更新镜像**：`git pull && docker compose build --no-cache`
- **清理容器**：`docker compose down`
- **定时运行**：可结合 `systemd`、`cron` 或容器编排平台进一步自动化。

## 常见问题与排查
| 问题 | 解决方案 |
| --- | --- |
| `python` 命令找不到或提示 "externally-managed-environment" | 使用 `python3 -m venv .venv` 创建虚拟环境后再激活；若系统未安装 `python3-venv`，可先通过包管理器安装。不要直接在系统环境中运行 `pip install`。 |
| 浏览器版本不匹配 | 重新安装匹配版本的 Chromium 与 Chromedriver，或在 Docker 中重新构建镜像。 |
| 无法打开图形界面（策略 A） | 检查 `xhost +local:docker` 是否执行，`DISPLAY` 与 `/tmp/.X11-unix` 是否正确挂载。 |
| VNC 无法连接（策略 B） | 确认服务器防火墙放行 5901 端口，可为 x11vnc 配置密码。 |
| Cookies 过期 | 再次执行任一登录策略覆盖 `weibo_cookies.json`。 |
| 数据未持久化 | 确保宿主机目录存在且拥有读写权限。 |

## 后续维护建议
- 定期同步 Chromium 与 Chromedriver 版本，避免 Selenium 报错。
- 监控日志目录容量，必要时接入日志聚合平台。
- 结合 `tests/` 目录下的单元测试与 `pytest`，在修改逻辑后快速回归验证。

## 许可证
本项目基于 MIT License 开源，详情见仓库内 `LICENSE` 文件。
