# Build image for Transcribe web version
FROM python:3.11-slim AS backend

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
CMD ["uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8000"]

FROM node:20 AS frontend
WORKDIR /app/client
COPY web/client/package.json ./
RUN npm install
COPY web/client ./
RUN npm run build

FROM backend AS final
COPY --from=frontend /app/client/dist ./web/client/dist
EXPOSE 8000
CMD ["uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8000"]
