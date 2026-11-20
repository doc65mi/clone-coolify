FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/clone
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home clone && mkdir /data && chown clone:clone /data
COPY app ./app
COPY VERSION .
USER clone
ENV CLONE_DATA_DIR=/data CLONE_SSH_DIR=/ssh PYTHONDONTWRITEBYTECODE=1
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787", "--workers", "1", "--no-access-log"]
