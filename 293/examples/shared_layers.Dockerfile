FROM node:18-alpine AS base

WORKDIR /app

RUN apk add --no-cache curl git

COPY package*.json ./

FROM base AS builder

RUN npm install

COPY . .

RUN npm run build

FROM base AS dev

RUN npm install --include=dev

COPY . .

CMD ["npm", "run", "dev"]

FROM nginx:alpine AS prod

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
