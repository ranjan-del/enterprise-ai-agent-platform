# Frontend image — build Angular, serve static via nginx.
# TODO: checklist "docker compose up brings up full stack".
# NOTE: scaffolding only — not built by the setup step.

# --- Build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# --- Serve stage ---
FROM nginx:alpine
# TODO: add nginx config that rewrites /api to the backend host.
COPY --from=build /app/dist/frontend /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
