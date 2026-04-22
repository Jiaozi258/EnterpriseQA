import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from config import Config

class RagService:
    def __init__(self):
        self.llm = ChatOllama(model=Config.LLM_MODEL)
        self.embeddings = OllamaEmbeddings(model=Config.EMBEDDING_MODEL)
        self.vector_db = Chroma(
            persist_directory=Config.CHROMA_DB_DIR,
            embedding_function=self.embeddings
        )

    def ingest_pdf(self, path: str, doc_id: int):
        loader = PyPDFLoader(path)
        docs = loader.load()
        
        for doc in docs:
            doc.metadata["doc_id"] = doc_id 
            
        splits = RecursiveCharacterTextSplitter(chunk_size=500).split_documents(docs)
        self.vector_db.add_documents(splits)
        print(f"✅ doc_id={doc_id} 的切片已成功存入向量库")

    def delete_pdf(self, doc_id: int):
        collection = self.vector_db._collection
        result = collection.get(where={"doc_id": doc_id})
        
        if result and result["ids"]:
            collection.delete(ids=result["ids"])
            print(f"🗑️ 已从向量库中彻底删除 doc_id={doc_id} 的所有数据")

    def query(self, question):
        retriever = self.vector_db.as_retriever()
        template = """请使用以下上下文来回答最后的问题。如果你不知道答案，就说你不知道，不要试图编造答案。
        上下文: {context}
        
        问题: {question}
        
        有用的回答:"""
        prompt = PromptTemplate.from_template(template)
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return rag_chain.invoke(question)

rag_instance = RagService()