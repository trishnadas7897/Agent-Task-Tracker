# --------------------------------------------------------------------------
# Agent Task Tracker - frontend (Vite build served by nginx)
# Two stages: node builder + nginx runtime. VITE_API_URL is consumed at
# BUILD time (Vite inlines env vars), pass it via `docker build --build-arg`.
# --------------------------------------------------------------------------

# ---------- stage 1: builder ----------
FROM node:20-alpine AS builder

WORKDIR /build

# Build-time arg the React bundle will be compiled against.
ARG VITE_API_URL=http://localhost:5000
ENV VITE_API_URL=${VITE_API_URL}

# Copy dependency manifests first so docker can cache npm install.
COPY package*.json ./
RUN npm ci --no-audit --no-fund --loglevel=warn

# Now bring in the rest of the source and build.
COPY . .
RUN npm run build

# ---------- stage 2: runtime ----------
FROM nginx:1.27-alpine AS runtime

# nginx config: SPA fallback to /index.html for HashRouter / BrowserRouter.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Built static assets.
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
