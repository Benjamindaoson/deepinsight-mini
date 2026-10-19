FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib \
    TZ=Europe/London MINI_MAX_JOBS=1 MINI_DATA_DIR=/persist/data MINI_OUTPUT_DIR=/persist/output
WORKDIR /app
COPY deployment/requirements-runtime.txt /app/requirements-runtime.txt
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY app /app/app
COPY deepinsight /app/deepinsight
COPY config /app/config
COPY deployment/seed /app/deployment/seed
EXPOSE 8080
CMD ["python", "-m", "app.railway_runtime"]
