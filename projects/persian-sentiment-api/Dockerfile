FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/app/.cache/huggingface \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /workspace

RUN groupadd --system app \
    && useradd --system --gid app --create-home app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app/.cache

COPY pyproject.toml README.md LICENSE ./
COPY app ./app

RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" \
    && python -m pip install --no-cache-dir ".[inference]"

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
