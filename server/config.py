# server/config.py
import os

class Config:
    # --- 基础配置 ---
    PROJECT_NAME = "EnterpriseQA"
    VERSION = "1.0.0"
    
    # --- 数据库配置 (MySQL) ---
    DB_HOST = "mysql_db"
    DB_PORT = 3306
    DB_USER = "root"
    DB_PASS = "123456" 
    DB_NAME = "db_enterprise_qa"
    
    # --- AI 模型配置 ---
    OLLAMA_BASE_URL = "http://host.docker.internal:11434"
    LLM_API_KEY = "ollama"  
    LLM_BASE_URL = OLLAMA_BASE_URL + "/v1"
    LLM_MODEL = "qwen2.5:7b"
    EMBEDDING_MODEL = "nomic-embed-text"
    
    
    # --- 路径配置 ---
    CHROMA_DB_DIR = "/app/chroma_db_v2"   
    UPLOAD_DIR = "/app/uploads"

# 确保文件夹存在
if not os.path.exists(Config.UPLOAD_DIR):
    os.makedirs(Config.UPLOAD_DIR)