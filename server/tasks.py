from celery import Celery
from rag_service import rag_instance
from database import SessionLocal, Document
import os

# 初始化 Celery，指定 Redis 作为消息队列 (Broker) 和结果存储 (Backend)
celery_app = Celery(
    'rag_tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

@celery_app.task(bind=True)
def async_ingest_pdf(self, file_path: str, doc_id: int):
    """
    这是一个后台异步任务：专门用来解析 PDF 和向量化
    """
    try:
        print(f"[{self.request.id}] 正在后台静默解析文档: {file_path}")
        
        # 1. 调用 RAG 引擎的耗时操作 (假设默认归属公开部门)
        rag_instance.ingest_pdf(file_path, doc_id, department="公开")
        
        # 2. 解析完成后，手动连一下数据库，把状态改为“已入库”
        with SessionLocal() as db:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.is_vectorized = True
                db.commit()
                
        return {"msg": "向量化成功", "doc_id": doc_id}
    except Exception as e:
        # 如果解析报错（比如模型没开），记录下来
        print(f"解析失败: {str(e)}")
        raise e