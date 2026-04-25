import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever  
from config import Config

class RagService:
    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vector_db = None

        self.reload_engine(
            api_key=Config.LLM_API_KEY, 
            base_url=Config.LLM_BASE_URL
        )

    def reload_engine(self, api_key: str, base_url: str):
        if not api_key:
            return False
            
        print(f"🔄 正在切换云端 AI : {base_url}")
        
        # 动态实例化云端模型 (以 DeepSeek / 硅基流动等兼容 OpenAI 格式的接口为例)
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=Config.LLM_MODEL
        )
        self.embeddings = OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=Config.EMBEDDING_MODEL,
            check_embedding_ctx_length=False
        )
        
        # 重新绑定向量数据库
        self.vector_db = Chroma(
            persist_directory=Config.CHROMA_DB_DIR,
            embedding_function=self.embeddings
        )
        return True

    def ingest_pdf(self, path: str, doc_id: int, department: str):
        loader = PyPDFLoader(path)
        docs = loader.load()
        
        for doc in docs:
            doc.metadata["doc_id"] = doc_id 
            doc.metadata["department"] = department
            
        splits = RecursiveCharacterTextSplitter(chunk_size=500).split_documents(docs)
        self.vector_db.add_documents(splits)
        print(f"✅ doc_id={doc_id} 的切片已成功存入向量库")

    def delete_pdf(self, doc_id: int):
        collection = self.vector_db._collection
        result = collection.get(where={"doc_id": doc_id})
        
        if result and result["ids"]:
            collection.delete(ids=result["ids"])
            print(f"🗑️ 已从向量库中彻底删除 doc_id={doc_id} 的所有数据")

    def query(self, question: str, user_department: str = "公开"):
        if not self.vector_db or not self.llm:
            return "AI 引擎未初始化，请先在设置中配置 API Key。"

        # 向量检索 (找相似)
        # 强制加上部门权限过滤，并取 Top 3
        vector_retriever = self.vector_db.as_retriever(
            search_kwargs={
                "k": 3,
                "filter": {"department": user_department}
            }
        )

        #BM25 关键词检索 
        # 企业级做法中，BM25 通常需要配合 ElasticSearch。
        # 每次查询时从 Chroma 中拉取当前部门的文本构建临时 BM25。
        # 真实生产环境中会有独立的全文索引库
        all_docs = self.vector_db.get(where={"department": user_department})
        
        if not all_docs or not all_docs['documents']:
            return "您的知识库中还没有任何文档，请先上传 PDF。"
            
        # 将 Chroma 返回的纯文本转化为 LangChain 需要的 Document 对象格式
        from langchain_core.documents import Document
        bm25_docs = [Document(page_content=text) for text in all_docs['documents']]
        
        bm25_retriever = BM25Retriever.from_documents(bm25_docs)
        bm25_retriever.k = 3 # BM25 也取 Top 3

        # 权重交叉 (向量占 60%，关键词占 40%)
        ensemble_retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.6, 0.4]
        )

        # 执行召回，获取合并后的片段
        docs = ensemble_retriever.invoke(question)
        
        # 将检索到的片段拼接成一段长文本，准备喂给大模型
        context_text = "\n\n".join([doc.page_content for doc in docs])

        # 生成最终的 Prompt 并向大模型提问
        prompt = PromptTemplate.from_template("""
        你是一个企业级智能助手。请严格根据以下提供的<内部知识>来回答问题。
        如果内部知识中没有相关信息，请直接回答“根据当前知识库无法回答”，绝不能胡编乱造。
        
        <内部知识>:
        {context}
        
        用户问题: {question}
        """)

        # 经典的 LCEL 链式调用
        chain = prompt | self.llm | StrOutputParser()
        
        # 返回 AI 的最终解答
        return chain.invoke({"context": context_text, "question": question})

rag_instance = RagService()