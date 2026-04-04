# app-login-service

基於 FastAPI + JWT 的使用者認證微服務，提供完整的 Token 生命週期管理。

---

## 技術選型

| 類別 | 選擇 | 說明 |
|---|---|---|
| 語言 | Python 3.13 | 最新穩定版，改善 error message 與型別推斷 |
| Web Framework | FastAPI 0.115+ | async-first，自動產生 OpenAPI 文件 |
| 套件管理 | uv | 比 pip/poetry 快 10-100 倍，內建 lockfile |
| ORM | SQLAlchemy 2.0 async | 成熟 async API，`mapped_column` 完整型別支援 |
| Migration | Alembic | SQLAlchemy 官方 migration 工具 |
| JWT | PyJWT 2.x | `python-jose` 有未修補 CVE，PyJWT 是業界標準 |
| 密碼雜湊 | bcrypt | 直接呼叫，避開 passlib + bcrypt 4.x 相容問題 |
| 設定管理 | pydantic-settings | 讀取 `.env`，型別自動驗證，`@lru_cache` 單例 |
| 限流 | slowapi | FastAPI 原生整合，支援 in-memory / Redis backend |
| 測試 | pytest + httpx + pytest-asyncio | 完整 async 測試支援 |
| Lint | ruff | 取代 flake8 + isort，速度極快 |
| 型別檢查 | mypy (strict) | 搭配 SQLAlchemy mypy plugin |

---

## 核心設計決策

### Refresh Token 採用不透明字串（非 JWT）

```
登入時：
  raw_token = secrets.token_urlsafe(64)  ← 回傳給客戶端
  token_hash = SHA-256(raw_token)         ← 存入資料庫

驗證時：
  計算 SHA-256(收到的 token) → 比對 DB
```

**原因：**
- JWT refresh token 一旦 secret 洩漏，所有 session 全部失效
- 不透明字串支援**精確的單一 session 撤銷**
- 每次 refresh 都輪換（rotation），舊 token 立即失效，防止重放攻擊

### Repository Pattern

```
Router（HTTP）→ Service（業務邏輯）→ Repository（資料存取）→ DB
```

Service 只依賴 Repository 介面，不碰 ORM，單元測試直接用 `AsyncMock` 注入，無需啟動資料庫。

### 統一 API 回應格式

所有端點一律回傳：

```json
{
  "success": true,
  "data": { ... },
  "message": "...",
  "errors": null
}
```

錯誤時：

```json
{
  "success": false,
  "data": null,
  "message": "Email already registered",
  "errors": null
}
```

### 測試隔離策略

使用 **Nested Transaction（Savepoint）** 模式：

```
Session-scoped engine（只建一次）
  └─ 每個 test 開一個 connection
       └─ begin_nested()  ← savepoint
            └─ 測試跑完 → rollback()
```

不需每個 test 重建 schema，速度快且完全隔離。

---

## API 端點

| Method | 路徑 | Auth | 說明 |
|---|---|---|---|
| POST | `/auth/register` | — | 註冊帳號 |
| POST | `/auth/login` | — | 登入，回傳 access + refresh token |
| POST | `/auth/refresh` | — | 換新 token，舊 refresh token 同步撤銷 |
| POST | `/auth/logout` | Bearer | 撤銷 refresh token |
| GET | `/auth/me` | Bearer | 取得當前使用者資訊 |
| GET | `/health` | — | 健康檢查 |

---

## 資料庫結構

```sql
users
  id               UUID PRIMARY KEY
  email            VARCHAR(255) UNIQUE
  username         VARCHAR(50) UNIQUE
  hashed_password  VARCHAR(255)
  is_active        BOOLEAN DEFAULT TRUE
  is_verified      BOOLEAN DEFAULT FALSE
  created_at       TIMESTAMPTZ
  updated_at       TIMESTAMPTZ

refresh_tokens
  id          UUID PRIMARY KEY
  token_hash  VARCHAR(64) UNIQUE   -- SHA-256 of raw token
  user_id     UUID → users.id CASCADE DELETE
  expires_at  TIMESTAMPTZ
  revoked_at  TIMESTAMPTZ NULL     -- NULL = 仍有效
  created_at  TIMESTAMPTZ
  user_agent  TEXT NULL
```

---

## 快速開始

### 安裝

```bash
# 安裝 uv（若尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安裝依賴
uv sync --dev
```

### 設定環境變數

```bash
cp .env.example .env
# 編輯 .env，至少設定 SECRET_KEY：
openssl rand -hex 32
```

### 執行 Migration

```bash
uv run alembic upgrade head
```

### 啟動服務

```bash
uv run uvicorn app.main:app --reload
```

服務啟動後：
- API 文件：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

---

## 測試

```bash
# 執行全部測試（含覆蓋率報告）
uv run pytest

# 只跑單元測試
uv run pytest tests/unit/

# 只跑整合測試
uv run pytest tests/integration/

# 查看覆蓋率報告（HTML）
uv run pytest --cov-report=html
open htmlcov/index.html
```

目前覆蓋率：**92%**（門檻 80%）

---

## 專案結構

```
src/app/
├── main.py               # FastAPI app factory + lifespan
├── core/
│   ├── config.py         # 環境變數設定
│   ├── database.py       # async engine + session
│   ├── security.py       # JWT + bcrypt
│   ├── dependencies.py   # FastAPI Depends（get_db, get_current_user）
│   ├── exceptions.py     # 領域例外 → HTTP status code
│   └── rate_limit.py     # slowapi 限流設定
├── models/
│   ├── user.py           # User ORM model
│   └── refresh_token.py  # RefreshToken ORM model
├── schemas/
│   ├── common.py         # APIResponse[T] 通用回應格式
│   ├── auth.py           # RegisterRequest, LoginRequest, TokenResponse...
│   └── user.py           # UserResponse
├── repositories/
│   ├── base.py           # 泛型 BaseRepository[T]
│   ├── user_repository.py
│   └── token_repository.py
├── services/
│   └── auth_service.py   # 所有業務邏輯
└── routers/
    ├── auth.py           # /auth/* 端點
    └── health.py         # /health 端點

tests/
├── conftest.py           # 測試 fixtures（nested transaction 隔離）
├── factories.py          # 測試資料建立 helper
├── unit/                 # 單元測試（Service + Security + Schemas）
└── integration/          # 整合測試（端到端 HTTP 測試）

migrations/
└── versions/             # Alembic migration 版本
```

---

## 切換到 PostgreSQL（正式環境）

`.env` 中修改：

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/logindb
ENVIRONMENT=production
```

正式環境不會自動建表，需手動執行 migration：

```bash
uv run alembic upgrade head
```

---

## 環境變數說明

| 變數 | 預設值 | 說明 |
|---|---|---|
| `SECRET_KEY` | 無（必填） | JWT 簽名金鑰，用 `openssl rand -hex 32` 產生 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./app.db` | 資料庫連線字串 |
| `ENVIRONMENT` | `development` | `development` / `testing` / `production` |
| `ALGORITHM` | `HS256` | JWT 演算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token 有效期（分鐘） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token 有效期（天） |
| `RATE_LIMIT_PER_MINUTE` | `10` | 認證端點每分鐘限制請求數 |
