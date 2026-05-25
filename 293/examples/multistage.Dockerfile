FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

RUN apk add --no-cache curl

RUN echo "Server configured"

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
