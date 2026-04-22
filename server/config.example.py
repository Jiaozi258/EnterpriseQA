# server/config.py
import os

class Config:
    # --- 基础配置 ---
    PROJECT_NAME = "EnterpriseQA"
    VERSION = "1.0.0"
    
    # --- 数据库配置 (MySQL) ---
    DB_HOST = "127.0.0.1"
    DB_PORT = 3308
    DB_USER = "root"
    DB_PASS = "your pw" 
    DB_NAME = "db_enterprise_qa"
    
    # --- AI 模型配置 ---
    # 想换 DeepSeek API，只需要改这里
    LLM_MODEL = "qwen2.5:7b"
    EMBEDDING_MODEL = "nomic-embed-text"
    OLLAMA_BASE_URL = "http://localhost:11434"
    
    # --- 路径配置 ---
    # 向量数据库存储路径
    CHROMA_DB_DIR = os.path.join(os.getcwd(), "chroma_db_v2")
    # 上传文件存储路径
    UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")

# 确保文件夹存在
if not os.path.exists(Config.UPLOAD_DIR):
    os.makedirs(Config.UPLOAD_DIR)