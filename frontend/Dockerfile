# Stage 1: Build the React Application
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
# Build-time env vars (baked into the static bundle)
ARG VITE_API_URL
ARG VITE_TABLEAU_REPORT_URL
ARG VITE_SENTRY_DSN
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_TABLEAU_REPORT_URL=$VITE_TABLEAU_REPORT_URL
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN

RUN npm run build

# Stage 2: Serve the Built Static Files via Nginx
FROM nginx:alpine

# Copy custom Nginx configuration to handle React Router client-side history API routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy Vite build output directly into Nginx web root directory
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
