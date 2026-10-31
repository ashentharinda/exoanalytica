# Stage 1: install dependencies and bake a baseline model (synthetic data) into the image
FROM python:3.11-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH PIP_DEFAULT_TIMEOUT=300 PIP_RETRIES=10
# torch on its own layer: a retry never repeats the other packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
COPY app app
COPY scripts scripts
RUN python -m scripts.train_synthetic

# Stage 2: slim, non-root runtime
FROM python:3.11-slim
RUN useradd -r -u 10001 -m exo && mkdir -p /data/jobs && chown exo /data/jobs
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/app /app/app
COPY --from=builder /build/weights /app/weights
ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/app PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
USER exo
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]