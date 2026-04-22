\#EnterpriseQA  - 企业级智能知识库系统



> 这是一个基于 Vue3 和 FastAPI 构建的企业级 RAG 知识库系统。

> 

> 

> 这是一个具备前后端分离、双库状态同步、历史记忆归档功能的完整系统架构。

> 

> 在该项目的开发中AI发挥了至关重要的辅助作用，该项目也是作者的学习项目。



\---



\## 核心特性 





* 双擎驱动架构：支持本地化部署（Ollama）与云端大模型 API。
* 知识全生命周期管理：支持 PDF 智能切片与向量注入，实现了基于 `Metadata` 标签的\*\*向量精准物理删除\*\*。
* 会话隔离与记忆回溯：采用 MySQL 关系型数据库沉淀对话历史，支持多线会话隔离、新建对话及一键清除记忆。
* 极致响应的现代化 UI：前端采用 Vite + Vue 3 驱动，Element Plus 定制，提供极简交互体验。



\---



\##  技术栈 



\### 前端 (Client)

\- \*\*核心框架\*\*: Vue 3 (Composition API) + Vite

\- \*\*UI 组件库\*\*: Element Plus

\- \*\*网络请求\*\*: Axios



\### 后端 (Server)

\- \*\*核心框架\*\*: FastAPI (Uvicorn 驱动)

\- \*\*数据库 ORM\*\*: SQLAlchemy + PyMySQL

\- \*\*AI 与逻辑编排\*\*: LangChain (核心层、社区组件)

\- \*\*向量数据库\*\*: ChromaDB

\- \*\*依赖管理\*\*: `uv`



\---

```sql
\##  快速开始



\### 1. 环境准备

在运行本项目前，请确保你的本地机器已安装以下环境：

\#Node.js (建议 v18+ )
\#Python (建议 3.10+ )
\#MySQL (运行于 3306 或 3308 端口)
\#\*\[可选]\* Ollama (如果你希望完全断网本地运行)



\### 2. 数据库配置

在你的 MySQL 中新建一个空数据库：


CREATE DATABASE db\_enterprise\_qa CHARACTER SET utf8mb4 COLLATE utf8mb4\_unicode\_ci;



\###3.后端部署



cd server



\# 使用 uv 一键安装所有依赖 (如果使用 pip，请查看 pyproject.toml 手动安装)

uv sync



\# 配置环境变量

\# 1. 复制 config.example.py 并重命名为 config.py

\# 2. 修改其中的 DB\_URL (填入你的数据库密码) 和 API\_KEY (如使用云端模型)

cp config.example.py config.py



\# 启动 FastAPI 服务

uv run uvicorn main:app --reload



\###4.前端部署



cd client



\# 安装前端依赖

npm install



\# 启动开发服务器

npm run dev



\##目录结构



EnterpriseQA/

├── client/                 # Vue 3 前端工程

│   ├── src/

│   │   ├── App.vue         # 主控页面 (布局、逻辑、组件聚合)

│   │   └── main.js         # 前端入口与全局配置

│   ├── index.html          # 网页元数据与 Favicon

│   └── package.json        

├── server/                 # FastAPI 后端工程

│   ├── main.py             # 核心路由 (上传、删除、问答、历史)

│   ├── rag\_service.py      # RAG 核心逻辑 (LCEL 架构, 向量注入与检索)

│   ├── database.py         # SQLAlchemy 模型定义 (用户、文档、会话、消息)

│   ├── config.py           # 核心配置项 

│   └── pyproject.toml      # 后端依赖清单

└── .gitignore              # 忽略打包文件及敏感密码配置

