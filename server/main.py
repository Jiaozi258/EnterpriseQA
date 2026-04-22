from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import shutil
from config import Config
from database import get_db, engine, Base, User, Document, ChatSession, ChatMessage
from rag_service import rag_instance

# 启动时自动创建所有数据表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EnterpriseQA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. 文档管理：上传 ---
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # A. 数据库预登记（获取 doc_id）
    # 暂时默认 uploader_id=1 (后续对接登录系统)
    new_doc = Document(filename=file.filename, uploader_id=1)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # B. 物理保存
    file_path = os.path.join(Config.UPLOAD_DIR, f"{new_doc.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 更新路径到数据库
    new_doc.file_path = file_path
    db.commit()

    # C. 异步/同步向量化（传入 doc_id）
    try:
        rag_instance.ingest_pdf(file_path, new_doc.id)
        new_doc.is_vectorized = True
        db.commit()
        return {"msg": "注入成功", "doc_id": new_doc.id}
    except Exception as e:
        db.delete(new_doc) # 如果向量化失败，回滚数据库
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

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
        if os.path.exists(doc.file_path):
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
async def chat(data: dict, db: Session = Depends(get_db)):
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
        answer = rag_instance.query(user_query)
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