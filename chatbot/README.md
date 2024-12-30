# CocoonChat

A smart chatbot system for monitoring and interacting with Weibo group chats.

## Overview
这是一个增强版的聊天机器人系统，支持微博群聊监控和命令行交互模式。主要功能包括：
- 微博群聊消息监控和自动回复
- 命令行交互模式
- 历史消息上下文支持
- Emoji 字符处理
- 数据持久化存储

## Requirements
- Python 3.8+
- Chrome 浏览器
- SQLite3
- OpenAI API 访问权限

## Installation
1. 克隆仓库
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 复制 `.env.example` 到 `.env` 并填写配置

## Configuration
在 `.env` 文件中配置以下信息：
```ini
# OpenAI API 配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=your_base_url


```

## Usage

### 命令行交互模式
直接与机器人对话：
```bash
python -m chatbot.main
```

### 微博监控模式
启动微博群聊监控：
```bash
python -m chatbot.main --monitor
```

## Features

### 微博群聊监控
- 自动监控指定群聊消息
- 处理 @ 机器人的消息
- 自动回复支持多行文本

### 命令行交互
- 直接在命令行与机器人对话
- 支持 'quit' 命令退出
- 保持历史对话上下文

### 数据存储
- 使用 SQLite 存储消息历史
- 支持消息检索和上下文分析

## Project Structure
```
chatbot/
├── main.py          # 主入口文件
├── handlers/        # 处理器模块
│   └── ai_interface.py
├── weibo/          # 微博相关模块
│   └── monitor.py
├── db/             # 数据库模块
│   └── sqlite_db.py
└── utils/          # 工具模块
    ├── config.py
    └── logger.py
```

## Development

### 添加新功能
1. 在相应模块目录下创建新文件
2. 在 `main.py` 中注册新功能
3. 更新文档和测试

### 调试
- 使用命令行模式进行功能测试
- 查看日志文件了解运行状态
- 使用 SQLite 客户端查看数据

## Troubleshooting
- 如果遇到导入错误，确保使用 `python -m chatbot.main` 运行
- 如果消息发送失败，检查 Chrome 版本和 ChromeDriver 是否匹配
- 如果数据库访问出错，检查权限和路径配置

## Contributing
欢迎提交 Pull Request 或提出 Issue。

## License
MIT License