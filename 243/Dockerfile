FROM node:18-alpine

RUN apk add --no-cache \
    git \
    curl \
    tar \
    gzip \
    docker-cli

WORKDIR /app

COPY package*.json ./
RUN npm install --only=production

COPY src/ ./src/
COPY config.yaml ./

RUN mkdir -p /app/workspace /app/cache /app/archives /app/logs

VOLUME ["/app/workspace", "/app/cache", "/app/archives", "/app/logs"]

EXPOSE 3000

ENV NODE_ENV=production

CMD ["node", "src/index.js"]
