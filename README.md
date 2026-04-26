```markdown
# EnterpriseQA - 企业级私有知识库

EnterpriseQA 是一个基于 RAG架构的现代化企业级文档问答系统。它允许用户上传内部文档，通过大模型与向量数据库进行深度解析，从而构建一个随时可检索、可交互的智能企业大脑。

本项目采用微服务架构设计，支持 **完全断网的本地大模型私有化部署**，同时也支持 **一键切换云端大模型 API**，在数据极致安全与无限算力之间提供完美的灵活性。

## 核心特性

-**双擎驱动 (Dual-Engine AI)**：支持通过 `config.py` 热重载无缝切换本地 Ollama 模型或云端大模型。
- **全异步后台处理 (Async Processing)**：深度集成 **Celery + Redis** 消息队列。海量 PDF 上传与向量化切片在后台静默运行，主 API 毫不阻塞，提供丝滑的前端体验。
-  **混合检索架构 (Hybrid Search)**：结合 ChromaDB 的高维向量语义检索与基于文档属性的精确过滤，有效降低大模型幻觉，确保回答精准溯源。
-  **容器化一键部署 (Dockerized)**：全栈环境（前端、FastAPI、MySQL、Redis、Celery Worker）被彻底隔离并编排进 Docker Compose，解决跨域、环境污染等问题。

## 技术栈 

- **AI 架构**: LangChain / Ollama / OpenAI API 协议
- **向量数据库**: ChromaDB (本地持久化)
- **后端框架**: FastAPI / Python 3.11 / SQLAlchemy
- **消息队列**: Celery / Redis
- **关系型数据库**: MySQL 8.x
- **前端部署**: Web UI (Nginx 反向代理)
- **运维编排**: Docker / Docker Compose

## 快速启动 (Quick Start)

### 1. 前置要求
- 安装并启动 [Docker Desktop](https://www.docker.com/) (Windows/Mac) 或 Docker Engine (Linux)。
- 如果你想使用本地私有模型，请安装 [Ollama](https://ollama.com/) 并提前拉取模型：
  ```bash
  ollama run qwen2.5:7b
  ollama pull nomic-embed-text
  ```

### 2. 克隆项目
```bash
git clone [https://github.com/你的用户名/EnterpriseQA.git](https://github.com/JiaoZi258/EnterpriseQA.git)
cd EnterpriseQA
```

### 3. 一键编译与启动
在终端（推荐使用 WSL2 或 Linux/Mac 终端）中执行：
```bash
sudo docker compose up --build -d
```
*启动完成后，系统将自动进行数据库表初始化、Redis 连接池建立以及 Celery Worker 监听。*

### 4. 访问系统
打开浏览器访问：`http://localhost`

## 核心配置 (Configuration)

本项目实现了配置与逻辑的完美剥离。所有的核心 AI 参数均可在 `server/config.py` 中修改。

**修改为本地 Ollama 驱动：**
```python
LLM_API_KEY = "ollama"
OLLAMA_BASE_URL = "[http://host.docker.internal:11434](http://host.docker.internal:11434)"
LLM_BASE_URL = OLLAMA_BASE_URL + "/v1"
LLM_MODEL = "qwen2.5:7b"
EMBEDDING_MODEL = "nomic-embed-text"
```

**修改为云端 API 驱动（以 DeepSeek/硅基流动为例）：**
```python
LLM_API_KEY = "sk-xxxxxxxxxxxxxxxxxxx" # 填入你的真实 Key
LLM_BASE_URL = "[https://api.siliconflow.cn/v1](https://api.siliconflow.cn/v1)"
LLM_MODEL = "deepseek-ai/DeepSeek-V3"
# 对应修改 Embedding 模型
```
* 修改配置后，请使用 `docker compose up --build -d` 重启容器以应用最新代码。*

## 常见问题排查 (Troubleshooting)

1. **上传文件后一直解析失败？**
   - 检查本地 Ollama 是否已启动并在后台运行。
   - 使用 `sudo docker compose logs --tail 50 worker` 查看后台 Celery 队列的具体报错。
2. **代码修改后没有生效？**
   - 触发了 Docker 的镜像缓存陷阱。每次修改 Python 代码后，必须携带 `--build` 参数重新启动容器。
3. **C 盘/系统盘空间爆满？**
   - 频繁打包会产生悬空镜像，请定期使用 `docker system prune -a --volumes` 清理无用容器和缓存。