FROM node:20-alpine

WORKDIR /app

ARG VITE_API_URL=http://localhost:8002
ENV VITE_API_URL=$VITE_API_URL

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

EXPOSE 3000

CMD ["npx", "serve", "dist", "-l", "3000"]
