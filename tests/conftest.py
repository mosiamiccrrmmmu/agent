import os

# Ensure required env vars exist before any app import
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-16-chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://agent:agent@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://agent:agent@localhost:5432/test")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEBUG", "true")
