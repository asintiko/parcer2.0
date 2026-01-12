# Frontend Build
FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Copy Telegram Web K files (already built in public/tweb)
# Note: public/tweb should contain pre-built telegram-web-k files

# Build application
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built files to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy Telegram Web K files
COPY --from=build /app/public/tweb /usr/share/nginx/html/tweb

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
