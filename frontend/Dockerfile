# ==============================================================================
# MergeMind Frontend Service Dockerfile
# Multi-stage Vite build and Nginx static server
# ==============================================================================
FROM node:24-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Nginx Alpine Runtime
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
