# --- 编译打包 ---
FROM node:22-slim as build-stage
WORKDIR /app
# 复制前端代码
COPY package*.json ./
RUN npm install
COPY . .
# 打包生成 dist 静态文件夹
RUN npm run build

# --- Nginx 部署 ---
FROM nginx:stable-alpine as production-stage
# 把上一阶段编译好的 dist 复制到 Nginx 的默认网页目录下
COPY --from=build-stage /app/dist /usr/share/nginx/html
# 把反向代理配置覆盖进去
COPY nginx.conf /etc/nginx/conf.d/default.conf
# 暴露 80 端口
EXPOSE 80
# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]