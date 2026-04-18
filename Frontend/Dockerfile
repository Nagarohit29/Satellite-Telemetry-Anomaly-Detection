# Build stage
FROM node:20-alpine AS build

# Metadata labels for Docker Hub
LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="1.2"
LABEL description="React Dashboard for Satellite Telemetry Anomaly Detection"

WORKDIR /app

# Copy package files from Frontend folder in root context
COPY Frontend/package*.json ./
RUN npm install

# Copy all Frontend source files
COPY Frontend/ .

# Build the production assets
RUN npm run build

# Production stage
FROM nginx:alpine

# Metadata labels for production image
LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="1.2"

# Install curl for healthcheck
RUN apk add --no-cache curl

# Copy built assets from build stage to Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY Frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]