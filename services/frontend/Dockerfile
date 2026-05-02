FROM node:20-slim AS construccion
WORKDIR /app
COPY . .
RUN echo ">>> PASO 1: iniciando npm install" && \
    npm install --no-audit --no-fund --verbose && \
    echo ">>> PASO 2: npm install terminado, iniciando build" && \
    npm run build && \
    echo ">>> PASO 3: build terminado, limpiando" && \
    rm -rf node_modules && \
    echo ">>> PASO 4: todo listo"

FROM nginx:stable
COPY --from=construccion /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
