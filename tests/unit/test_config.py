from app.core.config import Settings


def test_settings_default_construction():
    settings = Settings(
        POSTGRES_SERVER="db.local", REDIS_HOST="redis.local", QDRANT_HOST="qdrant.local"
    )
    assert settings.POSTGRES_SERVER == "db.local"
    assert (
        settings.DATABASE_URL
        == "postgresql+asyncpg://osint_user:osint_password@db.local:5432/osint_db"
    )
    assert settings.REDIS_URL == "redis://redis.local:6379/0"
