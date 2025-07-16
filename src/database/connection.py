# src/database/connection.py
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
import sqlite3
import os

# Database configuration - Updated to use the correct multi-tenant database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vritti_dev.db")


# SQLite-specific configuration for foreign keys
def _enable_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create engine with enhanced configuration
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20  # 20 second timeout for database locks
    } if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,  # Verify connections before use
    echo=False  # Set to True for SQL debugging
)

# Enable foreign keys for SQLite connections
if "sqlite" in DATABASE_URL:
    event.listen(Engine, "connect", _enable_foreign_keys)

# Create session with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Keep objects accessible after commit
)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Get a database session (for direct use outside FastAPI)"""
    return SessionLocal()


def verify_foreign_keys():
    """Verify that foreign keys are enabled"""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
        return bool(result[0]) if result else False


def get_database_info():
    """Get database information for debugging"""
    with engine.connect() as conn:
        # Check foreign keys
        fk_result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
        foreign_keys_enabled = bool(fk_result[0]) if fk_result else False

        # Check journal mode
        journal_result = conn.execute(text("PRAGMA journal_mode")).fetchone()
        journal_mode = journal_result[0] if journal_result else "unknown"

        # Get table count
        tables_result = conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        ).fetchone()
        table_count = tables_result[0] if tables_result else 0

        return {
            "database_url": DATABASE_URL,
            "foreign_keys_enabled": foreign_keys_enabled,
            "journal_mode": journal_mode,
            "table_count": table_count,
            "engine_url": str(engine.url)
        }


# Context manager for database transactions
class DatabaseTransaction:
    """Context manager for database transactions with proper error handling"""

    def __init__(self):
        self.db = None

    def __enter__(self):
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.db.rollback()
        else:
            self.db.commit()
        self.db.close()


# Multi-tenant helper functions
def get_tenant_db_session(tenant_id: str):
    """Get a database session with tenant context"""
    db = SessionLocal()
    # Set tenant context for row-level security (if implemented)
    # db.execute(f"SET app.current_tenant_id = '{tenant_id}'")
    return db


def execute_raw_sql(sql: str, params: dict = None):
    """Execute raw SQL with proper connection handling"""
    with engine.connect() as conn:
        if params:
            return conn.execute(text(sql), params)
        else:
            return conn.execute(text(sql))


# Health check function
def check_database_health():
    """Check if database is accessible and properly configured"""
    try:
        info = get_database_info()

        # Verify we can connect
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Check if multi-tenant tables exist
        with engine.connect() as conn:
            tenant_table_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'")
            ).fetchone()

        return {
            "status": "healthy",
            "database_info": info,
            "multi_tenant_ready": bool(tenant_table_exists),
            "connection_test": "passed"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection_test": "failed"
        }


if __name__ == "__main__":
    # Test the database connection
    print("🔍 Testing database connection...")
    health = check_database_health()

    if health["status"] == "healthy":
        print("✅ Database connection successful!")
        info = health["database_info"]
        print(f"   📁 Database: {info['database_url']}")
        print(f"   🔗 Foreign Keys: {'✅ Enabled' if info['foreign_keys_enabled'] else '❌ Disabled'}")
        print(f"   📝 Journal Mode: {info['journal_mode']}")
        print(f"   📊 Tables: {info['table_count']}")
        print(f"   🏢 Multi-tenant: {'✅ Ready' if health['multi_tenant_ready'] else '❌ Not configured'}")
    else:
        print("❌ Database connection failed!")
        print(f"   Error: {health['error']}")