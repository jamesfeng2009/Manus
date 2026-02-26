# Manus

通用型 AI Agent（自主智能体）系统。

## 特性

- 🤖 **多模型支持**: OpenAI, Anthropic, DeepSeek, 阿里 Qwen, 月之暗面 Kimi, MiniMax, 智谱 GLM, 字节 Doubao, 腾讯 HunYuan, Google Gemini
- 🧠 **四层记忆系统**: Working, Episodic, Semantic, Procedural Memory
- 🔧 **丰富工具集**: 搜索、浏览器、代码执行、文件管理
- 👥 **多Agent协作**: Planner + Executor + Verifier 架构
- 🌐 **RESTful API**: 基于 LiteStar 的高性能 API
- 📦 **Docker 支持**: 一键部署

## 快速开始

### 安装

```bash
pip install -e .
```

### 配置

复制环境变量模板:

```bash
cp .env.example .env
```

编辑 `.env` 添加 API Key:

```bash
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
# ... 其他 API Keys
```

### 使用 CLI

```bash
# 执行任务
python -m manus.cli.main run "分析这个代码"

# 交互模式
python -m manus.cli.main interact

# 查看模型
python -m manus.cli.main models
```

### 使用 API

```bash
# 启动服务
litestar run

# 或使用 Docker
docker-compose up
```

## API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/tasks` | 创建任务 |
| GET | `/tasks` | 列表任务 |
| GET | `/tasks/{id}` | 获取任务 |
| POST | `/execute` | 执行任务 |
| GET | `/models` | 模型列表 |
| GET | `/health` | 健康检查 |

## 项目结构

```
manus/
├── agents/         # Agent 实现
├── api/            # REST API
├── cli/            # CLI 工具
├── config/         # 配置管理
├── context/        # 跨任务上下文
├── core/           # 核心类型和常量
├── memory/         # 记忆系统
├── models/         # 模型适配器
├── multimodal/     # 多模态支持
├── tasks/          # 任务管理
└── tools/          # 工具集
```

## 文档

- [架构设计](docs/ARCHITECTURE.md)

## License

MIT
