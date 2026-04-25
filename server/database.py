from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
from config import Config

# 1. 动态拼接连接字符串
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{Config.DB_USER}:{Config.DB_PASS}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"


# 2. 创建数据库引擎
# echo=True 可以在终端看到程序执行的真实 SQL 语句，方便修 Bug
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False, 
    pool_size=5,      # 连接池大小
    max_overflow=10   # 超过连接池后最多允许再开几个连接
)

# 3. 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 声明基类 (以后所有的数据库表都要继承它)
Base = declarative_base()

# 1. 用户表
class User(Base):
    __tablename__ = "sys_user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255)) #  绝对不能存明文密码
    department = Column(String(50))       # 部门标签 (如 "HR", "IT", "Finance")
    created_at = Column(DateTime, default=datetime.now)

# 2. 文档表 (用于管理用户上传的文件)
class Document(Base):
    __tablename__ = "knowledge_document"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    file_path = Column(String(500))
    uploader_id = Column(Integer, ForeignKey("sys_user.id")) # 谁上传的
    is_vectorized = Column(Boolean, default=False) # 是否已成功写入 Chroma
    created_at = Column(DateTime, default=datetime.now)
    department_scope = Column(String(50)) # 该文档对应特定部门

# 3. 对话归档表 (左侧历史列表里的某一次“新建对话”)
class ChatSession(Base):
    __tablename__ = "chat_session"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("sys_user.id"))
    title = Column(String(100), default="新对话") # 例如："关于报销制度的讨论"
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联消息
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete")

# 4. 会话历史记录表 (具体的聊天内容)
class ChatMessage(Base):
    __tablename__ = "chat_message"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_session.id"))
    role = Column(String(20)) # "user" 或 "assistant"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("ChatSession", back_populates="messages")

# 5. 系统配置表 (用于存储 API Key 等)
class SysConfig(Base):
    __tablename__ = "sys_config"
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(50), unique=True, index=True) # 比如 "api_key"
    config_value = Column(Text) # 对应的配置值

# 5. 依赖项 (Dependency)：给 FastAPI 用的开关
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
