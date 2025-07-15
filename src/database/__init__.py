# src/database/__init__.py
from .connection import (
    get_db,
    create_tables,
    get_db_session,
    check_database_health,
    get_database_info,
    DatabaseTransaction,
    Base,
    engine,
    SessionLocal
)

# Import models from the new location
try:
    from src.models.tenant import (
        Tenant,
        TenantUser,
        SubscriptionPlan,
        TenantUsage,
        TenantAPIKey,
        Document,
        Invoice,
        AuditLog,
        WebhookEndpoint
    )
except ImportError:
    # Models not yet created
    pass

__all__ = [
    'get_db',
    'create_tables',
    'get_db_session',
    'check_database_health',
    'get_database_info',
    'DatabaseTransaction',
    'Base',
    'engine',
    'SessionLocal',
    # Models (if available)
    'Tenant',
    'TenantUser',
    'SubscriptionPlan',
    'TenantUsage',
    'TenantAPIKey',
    'Document',
    'Invoice',
    'AuditLog',
    'WebhookEndpoint'
]