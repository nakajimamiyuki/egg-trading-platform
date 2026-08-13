# 构建阶段
FROM node:20 AS build
WORKDIR /app
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# 运行阶段: nginx 托管静态产物 + 反代 /api
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
