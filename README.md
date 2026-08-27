# SmartOps-AI-Agent 🛠️

> **基于 LangChain + FastAPI 构建的电商 / 物联网垂直领域 AI 客服与数据分析系统**，支持知识库 RAG 问答、多 Agent 任务路由、结构化数据自动分析与图表生成。

**本项目展示了我在大模型应用开发中的工程化能力：不仅懂 Prompt 和 RAG 原理，还具备独立编写 Python 后端接口、本地向量数据库、pandas 数据分析，以及前后端联调（SSE 流式）的实际落地能力，可快速适应企业私有化部署需求。**

---

## 🏗️ 整体架构

```text
用户提问（Web 前端，打字机流式输出）
        │  fetch / POST /api/chat  (SSE text/event-stream)
        ▼
[ FastAPI 后端 ]
        │
        ▼
[ Agent 路由器 RouterAgent ]  ← LLM 意图分类 + 关键词降级兜底
        ├── 1️⃣ knowledge   → 业务知识库 Agent（RAG：BGE 本地向量化 + 余弦检索 + LLM 生成）
        ├── 2️⃣ order       → 订单 / 设备状态查询 Agent（本地 CSV 检索，模拟外部 API）
        ├── 3️⃣ data        → 数据分析 Agent（pandas 统计 + matplotlib 图表）
        └── 4️⃣ human       → 兜底 / 转人工 Agent（闲聊、强情绪转人工）
```

| 模块 | 技术要点 | 命中 JD |
|---|---|---|
| RAG 知识库 | `RecursiveCharacterTextSplitter` 切分 + `BAAI/bge-small-zh-v1.5` 本地 Embedding + NumPy 向量库（零第三方依赖） | 向量检索 / 私有化部署 / 解决幻觉 |
| 多 Agent 路由 | LLM 意图分类 + 关键词规则降级，调度 4 个子 Agent | Agent / LangChain 工作流编排 |
| 数据分析 | `pandas` 读取订单 / 设备故障 CSV，`matplotlib` 生成图表（含中文字体适配） | 数据 + AI 提升业务效率 |
| 流式对话 | FastAPI `StreamingResponse` + SSE，前端打字机效果 | 生产级接口经验 |
| 数据入库 | Web 端一键上传 + `POST /api/ingest`，支持 txt / md / pdf / docx | 全生命周期 |

---

## 🚀 快速开始

```bash
# 1. 创建虚拟环境并安装依赖
python -m venv .venv
# Windows: .venv\Scripts\activate

# 2. 配置 LLM 网关（复制 .env.example 为 .env，填入你的 API Key）
cp .env.example .env

# 3. 安装依赖
pip install -r requirements.txt

# 4. 生成示例数据（订单 CSV + 设备故障 CSV + 知识库文档）并完成 RAG 入库
python scripts/seed_data.py

# 5. 启动服务（浏览器访问 http://127.0.0.1:8000）
uvicorn app.main:app --reload --port 8000
```

> 国内网络首次运行会自动使用 HF 镜像（hf-mirror.com）下载约 100MB 的 BGE 模型，如已有 `deepseek-rag-qa/data/models` 缓存会自动复用，跳过下载。

## 🐳 Docker 部署

```bash
# 1. 准备好 .env（从 .env.example 复制并填入 API Key）
cp .env.example .env

# 2. 构建并后台启动
docker compose up --build -d

# 3. 打开
# http://127.0.0.1:8000
```

首次启动时，容器入口脚本会自动探测示例数据与向量索引；若为空 volume 会自动执行 `scripts/seed_data.py` 完成数据生成和 RAG 入库，无需手动进入容器。

## 💬 试一下

打开 `http://127.0.0.1:8000`，输入：

| 输入 | 命中的 Agent | 演示效果 |
|---|---|---|
| 我的榨汁机坏了怎么办？ | 📚 知识库 Agent | 依据说明书 RAG 回答 + 引用来源 |
| 保修期是多久？ | 📚 知识库 Agent | 售后政策检索 |
| 查询订单 ORD-2026-00123 | 📦 订单查询 Agent | 返回订单详情 |
| 帮我分析各品类销售情况 | 📊 数据分析 Agent | 品类柱状图 |
| 分析最近设备故障率 | 📊 数据分析 Agent | 故障码分布饼图 + 月度趋势 |
| 我要转人工投诉 | 🤝 兜底 Agent | 转人工提示 |

## 🔌 核心接口

- `POST /api/chat` — SSE 流式对话，事件协议：`meta`(路由意图) → `delta`(文本分片) → `chart`(图表) → `sources`(引用) → `done`
- `POST /api/ingest` — 上传文档入库（txt/md/pdf/docx）
- `GET /api/health` / `GET /api/stats` — 健康检查与知识库统计

## 🧪 运行测试

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

测试覆盖：意图路由关键词兜底、NumPy 向量库增删查/持久化、订单/设备 CSV 查询、文本切分器。

## 🧩 项目结构

```text
SmartOps-AI-Agent/
├── app/
│   ├── main.py            # FastAPI 入口 + SSE
│   ├── dispatcher.py      # Agent 调度器
│   ├── router.py          # 意图路由
│   ├── knowledge.py       # RAG 管线
│   ├── embeddings.py      # 本地 BGE Embedding
│   ├── vectorstore.py     # NumPy 向量库
│   ├── chunker.py         # 文本切分
│   ├── loader.py          # 文档加载
│   └── agents/            # 4 个子 Agent
├── web/index.html         # 聊天前端（打字机 + 图表）
├── scripts/
│   ├── seed_data.py       # 示例数据生成 + 入库
│   └── docker_entrypoint.sh # Docker 首次启动自动初始化
├── tests/                 # pytest 单元测试
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── data/                  # CSV / 向量索引 / 图表 / 模型缓存（生成物）
```

## 🔄 替换为自己的 LLM

本项目使用 **OpenAI 兼容接口**，只需修改 `.env` 中的 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`，即可无缝切换到 DeepSeek、通义、智谱、或企业内部网关，**不需要改任何代码**。

---

*面向 电商客服 / 物联网售后 岗位面试打造的垂直领域落地项目。*
