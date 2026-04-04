FROM python:3.13-slim

WORKDIR /app

# 複製 uv binary（從官方 image）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 先複製 lock file，讓 layer cache 發揮效果
COPY pyproject.toml uv.lock ./

# 安裝 production 依賴（不含 project 本身，方便 cache）
RUN uv sync --frozen --no-dev --no-install-project

# 複製 source code
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini ./

# 安裝 project
RUN uv sync --frozen --no-dev

# 建立非 root 使用者
RUN useradd -r -u 1001 -s /bin/false appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
