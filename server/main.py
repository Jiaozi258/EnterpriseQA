from fastapi import FastAPI, Depends, UploadFile, File, HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import shutil
from config import Config
from database import get_db, engine, Base, User, Document, ChatSession, ChatMessage,SysConfig
from rag_service import rag_instance
from tasks import async_ingest_pdf
from celery.result import AsyncResult
from database import SessionLocal

# 定义令牌的钥匙和规则
SECRET_KEY = "ℼ潤瑣灹⁥瑨汭㰾瑨汭㰾敨摡㰾敭慴挠慨獲瑥∽瑵ⵦ㘱㸢琼瑩敬唾瑮瑩敬⁤潄畣敭瑮⼼楴汴㹥⼼敨摡㰾潢祤猠祴敬∽慰摤湩㩧〱硰㸢뷤붥裦꾘뷤릈⼼潢祤㰾栯浴㹬" #一段极其复杂的乱码并且储存在环境变量中
ALGORITHM = "HS256"

# 告诉前端，拿着账号密码去 /api/login 换令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

# 解析令牌，认出用户身份
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="身份验证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 JWT 令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # 从数据库查出这个人的全部信息（包括他的部门）
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def init_ai_engine(db: Session):
    """
    系统启动时，尝试从数据库加载配置并初始化 AI 引擎
    """
    api_key_record = db.query(SysConfig).filter(SysConfig.config_key == "api_key").first()
    base_url_record = db.query(SysConfig).filter(SysConfig.config_key == "base_url").first()
    
    if api_key_record and api_key_record.config_value:
        print(f"🚀 检测到之前的配置，正在初始化 AI 引擎...")
        rag_instance.reload_engine(
            api_key=api_key_record.config_value,
            base_url=base_url_record.config_value if base_url_record else "https://api.siliconflow.cn/v1"
        )

# 启动时自动创建所有数据表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EnterpriseQA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---0. 设置接口 ---

@app.get("/api/settings")
async def get_settings(db: Session = Depends(get_db)):
    # 从数据库读取
    api_key = db.query(SysConfig).filter(SysConfig.config_key == "api_key").first()
    base_url = db.query(SysConfig).filter(SysConfig.config_key == "base_url").first()
    
    return {
        "api_key": api_key.config_value if api_key else "",
        "base_url": base_url.config_value if base_url else "https://api.siliconflow.cn/v1"
    }

@app.post("/api/settings")
async def save_settings(data: dict, db: Session = Depends(get_db)):
    api_key = data.get("api_key")
    base_url = data.get("base_url")

    # 1. 持久化到 MySQL (使用 upsert 逻辑：有则更新，无则插入)
    for key, val in {"api_key": api_key, "base_url": base_url}.items():
        record = db.query(SysConfig).filter(SysConfig.config_key == key).first()
        if record:
            record.config_value = val
        else:
            db.add(SysConfig(config_key=key, config_value=val))
    db.commit()

    # 2. 触发 AI 引擎热重载
    success = rag_instance.reload_engine(api_key, base_url)
    
    if success:
        return {"msg": "配置已保存，引擎已就绪"}
    else:
        raise HTTPException(status_code=500, detail="配置已保存但引擎启动失败")

# --- 1. 文档管理：上传 ---
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # A. 数据库预登记（获取 doc_id）(此时 is_vectorized 默认为 False)
    new_doc = Document(filename=file.filename, uploader_id=1, department_scope="公开")
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # B. 物理保存
    file_path = os.path.join(Config.UPLOAD_DIR, f"{new_doc.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
    
    # 更新路径到数据库
    new_doc.file_path = file_path
    db.commit()

    # 把耗时的向量化任务直接丢给 Celery 队列，立刻拿号走人
    task = async_ingest_pdf.delay(file_path, new_doc.id)

    # 直接给前端返回一个任务追踪单号
    return {"msg": "文件已放入后台解析队列", "task_id": task.id, "doc_id": new_doc.id}

# 供前端轮询查询任务进度的接口
@app.get("/api/upload/status/{task_id}")
async def get_upload_status(task_id: str):
    # 根据单号去 Redis 里查任务状态
    task_result = AsyncResult(task_id, app=async_ingest_pdf.app)
    return {
        "task_id": task_id,
        "status": task_result.status, # 可能是 PENDING, SUCCESS, FAILURE
        "result": str(task_result.result) if task_result.ready() else None
    }

# --- 2. 文档列表查询 ---
@app.get("/api/documents")
async def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    return [{"id": d.id, "name": d.filename, "status": d.is_vectorized, "time": d.created_at} for d in docs]

# --- 3. 文档删除 ---
@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # A. 从 Chroma 中删除向量
        rag_instance.delete_pdf(doc_id)
        
        # B. 删除文件
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            
        # C. 从 MySQL 中删除记录
        db.delete(doc)
        db.commit()
        return {"msg": "文档及相关知识已彻底清除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

# --- 4. 会话管理：获取历史会话列表 ---
@app.get("/api/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    # 获取所有的对话主题 (按时间倒序排)
    # 暂定 uploader_id=1，未来对接 JWT 登录后替换为当前登录用户
    sessions = db.query(ChatSession).filter(ChatSession.user_id == 1).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "time": s.created_at} for s in sessions]

# --- 5. 会话管理：获取某个会话的具体聊天记录 ---
@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    return [{"role": m.role, "content": m.content} for m in messages]

# --- 6. 智能问答接口 ---
@app.post("/api/chat")
async def chat(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_query = data.get("query")
    session_id = data.get("session_id") # 前端如果传了，说明是在旧帖子里回帖
    
    if not user_query:
        raise HTTPException(status_code=400, detail="提问内容不能为空")

    # A. 会话档案建立：如果是新对话，先建个文件夹 (ChatSession)
    if not session_id:
        # 取问题的前15个字当标题
        title = user_query[:15] + "..." if len(user_query) > 15 else user_query
        new_session = ChatSession(user_id=1, title=title)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = new_session.id # 获取刚建好的 id

    # B. 记录用户的提问 (ChatMessage)
    user_msg = ChatMessage(session_id=session_id, role="user", content=user_query)
    db.add(user_msg)
    db.commit()

    # C. 调用 RAG 大脑进行思考
    try:
        answer = rag_instance.query(user_query, user_department=current_user.department)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 思考时出故障了: {str(e)}")

    # D. 记录 AI 的回答 (ChatMessage)
    ai_msg = ChatMessage(session_id=session_id, role="assistant", content=answer)
    db.add(ai_msg)
    db.commit()

    # E. 把答案和当前的档案号一起退给前端
    return {"answer": answer, "session_id": session_id}

# --- 7. 会话管理：删除会话档案 ---
@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    session_to_delete = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session_to_delete:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    db.delete(session_to_delete)
    db.commit() # 由于我们在模型里加了 cascade="all, delete"，这会把相关的消息一并删掉
    return {"msg": "记录已删除"}