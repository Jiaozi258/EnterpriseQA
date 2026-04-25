# 使用轻量级的 Python 3.10 作为基础环境
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 把 server 目录下的所有文件都塞进集装箱
COPY . /app

# 安装 uv，并用它极速同步所有的依赖包
RUN pip install uv
RUN uv sync

RUN uv add langchain langchain-community rank-bm25 langchain-openai

# 暴露 8000 端口
EXPOSE 8000