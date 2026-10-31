# Stage 1: build static assets
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json .
COPY src src
RUN npm run build

# Stage 2: unprivileged nginx serves them and proxies /api to the backend
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
