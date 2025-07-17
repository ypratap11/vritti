# src/api/v1/conversation.py - Updated with config integration

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import json
import uuid
import logging
from datetime import datetime, timedelta

from src.database.connection import get_db
from src.models.tenant import Tenant, TenantUser
from src.agents.ask_vritti import AskVrittiAI
from src.core.config import get_settings
from sqlalchemy import text


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


# Pydantic models (same as before)
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}


class ChatResponse(BaseModel):
    response: str
    session_id: str
    intent: str
    action_required: bool = False
    action_type: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    suggested_responses: Optional[List[str]] = None
    timestamp: str
    llm_used: Optional[str] = None
    cost: Optional[float] = None
    confidence: Optional[float] = None


class PhoneWebhook(BaseModel):
    call_sid: str
    from_number: str
    to_number: str
    speech_result: Optional[str] = None
    digits: Optional[str] = None
    call_status: str


# WebSocket Manager (same as before)
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.tenant_connections: Dict[str, List[str]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, tenant_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        if tenant_id not in self.tenant_connections:
            self.tenant_connections[tenant_id] = []
        self.tenant_connections[tenant_id].append(session_id)

    def disconnect(self, session_id: str, tenant_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if tenant_id in self.tenant_connections:
            self.tenant_connections[tenant_id] = [
                sid for sid in self.tenant_connections[tenant_id] if sid != session_id
            ]

    async def send_personal_message(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")

    async def broadcast_to_tenant(self, message: dict, tenant_id: str):
        if tenant_id in self.tenant_connections:
            for session_id in self.tenant_connections[tenant_id]:
                await self.send_personal_message(message, session_id)


# Initialize router and dependencies
router = APIRouter(prefix="/conversation", tags=["conversation"])
security = HTTPBearer()
websocket_manager = WebSocketManager()


# Initialize Ask Vritti with settings from config
def get_ask_vritti() -> AskVrittiAI:
    """Get AskVritti instance with configuration from settings"""

    # Validate API keys are available
    available_providers = settings.validate_api_keys()

    if not available_providers:
        logger.error("No LLM API keys configured!")
        raise RuntimeError(
            "No LLM API keys found. Please configure GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")

    logger.info(f"Initializing AskVritti with providers: {list(available_providers.keys())}")

    # Get LLM config from settings
    llm_config = settings.get_llm_config()

    return AskVrittiAI(
        gemini_api_key=llm_config["gemini_api_key"],
        openai_api_key=llm_config["openai_api_key"],
        anthropic_api_key=llm_config["anthropic_api_key"],
        gcp_project_id=llm_config["gcp_project_id"]
    )


# Initialize Ask Vritti
try:
    ask_vritti = get_ask_vritti()
    logger.info("✅ AskVritti initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize AskVritti: {e}")
    ask_vritti = None


# Dependency to get Ask Vritti
async def get_ask_vritti_dependency() -> AskVrittiAI:
    """Dependency to ensure AskVritti is available"""
    if ask_vritti is None:
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable. Please check API key configuration."
        )
    return ask_vritti


# Authentication dependency (enhanced)
async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> TenantUser:
    """Get current authenticated user from JWT token"""

    # TODO: Implement proper JWT validation here
    # For development, return demo user
    if settings.debug:
        user = db.query(TenantUser).filter(
            TenantUser.email == "admin@demo.vritti.ai"
        ).first()

        if not user:
            # Create demo user if not exists
            from src.models.tenant import Tenant
            tenant = db.query(Tenant).filter(Tenant.name == "Demo Tenant").first()
            if not tenant:
                tenant = Tenant(
                    id="demo-tenant-id",
                    name="Demo Tenant",
                    domain="demo.vritti.ai"
                )
                db.add(tenant)
                db.commit()

            user = TenantUser(
                id="demo-user-id",
                tenant_id=tenant.id,
                email="admin@demo.vritti.ai",
                name="Demo Admin"
            )
            db.add(user)
            db.commit()

        return user
    else:
        # Production JWT validation
        raise HTTPException(status_code=401, detail="JWT validation not implemented")


# API Endpoints (same logic, enhanced error handling)

@router.post("/chat", response_model=ChatResponse)
async def chat_message(
        message: ChatMessage,
        user: TenantUser = Depends(get_current_user),
        ask_vritti: AskVrittiAI = Depends(get_ask_vritti_dependency),
        db: Session = Depends(get_db)
):
    """Process a chat message from the web interface"""
    try:
        session_id = message.session_id or str(uuid.uuid4())

        context = ask_vritti.get_conversation_context(session_id)
        if not context:
            context = ask_vritti.create_conversation_context(
                session_id=session_id,
                tenant_id=user.tenant_id,
                user_id=user.id
            )

        ai_response = await ask_vritti.process_message(message.message, context)

        response = ChatResponse(
            response=ai_response.text,
            session_id=session_id,
            intent=ai_response.intent.value,
            action_required=ai_response.action_required,
            action_type=ai_response.action_type,
            action_data=ai_response.action_data,
            suggested_responses=ai_response.suggested_responses,
            timestamp=datetime.now().isoformat(),
            llm_used=ai_response.llm_used.value if ai_response.llm_used else None,
            cost=ai_response.cost,
            confidence=ai_response.confidence
        )

        await websocket_manager.send_personal_message(response.dict(), session_id)
        return response

    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint with API key validation"""
    try:
        available_providers = settings.validate_api_keys()

        return {
            "status": "healthy",
            "available_llm_providers": list(available_providers.keys()),
            "ask_vritti_initialized": ask_vritti is not None,
            "settings_loaded": True,
            "gcp_project": settings.gcp_project_id
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/config/validate")
async def validate_configuration():
    """Validate all configuration settings"""
    try:
        validation_results = {
            "api_keys": settings.validate_api_keys(),
            "gcp_setup": {
                "project_id": settings.gcp_project_id,
                "processor_id": settings.gcp_processor_id,
                "credentials_path": settings.google_application_credentials
            },
            "database": {
                "url_configured": settings.database_url is not None
            },
            "security": {
                "secret_key_set": bool(settings.secret_key),
                "jwt_algorithm": settings.jwt_algorithm
            }
        }

        return {
            "status": "validated",
            "results": validation_results,
            "environment": settings.debug
        }

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.post("/test-chat", response_model=ChatResponse)
async def test_chat_message(
        message: ChatMessage,
        ask_vritti: AskVrittiAI = Depends(get_ask_vritti_dependency),
        db: Session = Depends(get_db)
):
    """Test chat message without authentication - FOR TESTING ONLY"""

    try:
        # Use demo tenant for testing
        demo_tenant_id = "demo-tenant-id"
        demo_user_id = "demo-user-id"

        session_id = message.session_id or str(uuid.uuid4())

        context = ask_vritti.get_conversation_context(session_id)
        if not context:
            context = ask_vritti.create_conversation_context(
                session_id=session_id,
                tenant_id=demo_tenant_id,
                user_id=demo_user_id
            )

        ai_response = await ask_vritti.process_message(message.message, context)

        response = ChatResponse(
            response=ai_response.text,
            session_id=session_id,
            intent=ai_response.intent.value,
            action_required=ai_response.action_required,
            action_type=ai_response.action_type,
            action_data=ai_response.action_data,
            suggested_responses=ai_response.suggested_responses,
            timestamp=datetime.now().isoformat(),
            llm_used=ai_response.llm_used.value if ai_response.llm_used else None,
            cost=ai_response.cost,
            confidence=ai_response.confidence
        )

        return response

    except Exception as e:
        logger.error(f"Error processing test chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.get("/test-simple")
async def simple_test():
    """Super simple test endpoint"""
    return {
        "message": "Hello from Vritti AI!",
        "status": "working",
        "timestamp": datetime.now().isoformat()
    }


async def get_full_database_schema(db: Session = Depends(get_db)):
    """Get complete database schema with constraints, indexes, and foreign keys"""
    try:
        # Get all tables
        tables_result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in tables_result.fetchall()]

        schema_info = {}

        for table in tables:
            # Get table structure
            table_info = db.execute(text(f"PRAGMA table_info({table});")).fetchall()

            # Get foreign keys
            fk_info = db.execute(text(f"PRAGMA foreign_key_list({table});")).fetchall()

            # Get indexes
            index_info = db.execute(text(f"PRAGMA index_list({table});")).fetchall()

            # Get CREATE TABLE statement
            create_sql_result = db.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:table_name;"),
                {"table_name": table}
            ).fetchone()

            schema_info[table] = {
                "columns": [
                    {
                        "cid": row[0],
                        "name": row[1],
                        "type": row[2],
                        "not_null": bool(row[3]),
                        "default_value": row[4],
                        "is_primary_key": bool(row[5])
                    }
                    for row in table_info
                ],
                "foreign_keys": [
                    {
                        "id": row[0],
                        "seq": row[1],
                        "table": row[2],
                        "from_column": row[3],
                        "to_column": row[4],
                        "on_update": row[5],
                        "on_delete": row[6],
                        "match": row[7]
                    }
                    for row in fk_info
                ],
                "indexes": [
                    {
                        "seq": row[0],
                        "name": row[1],
                        "unique": bool(row[2])
                    }
                    for row in index_info
                ],
                "create_sql": create_sql_result[0] if create_sql_result else None
            }

        return {
            "status": "success",
            "total_tables": len(tables),
            "tables": tables,
            "schema": schema_info
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# Replace the create-all-dummy-data endpoint with this corrected version:

@router.post("/debug/create-all-dummy-data-corrected")
async def create_all_dummy_data_corrected(db: Session = Depends(get_db)):
    """Create comprehensive dummy data matching actual model structure"""
    try:
        dummy_data_created = []

        # 1. Create dummy subscription plan FIRST (required for tenant)
        try:
            db.execute(text("""
                INSERT OR IGNORE INTO subscription_plans (
                    id, name, slug, description, price_monthly, price_yearly,
                    document_limit, user_limit, storage_limit_gb, api_calls_limit,
                    features, is_active, created_at, updated_at, schema_version
                ) VALUES (
                    'plan-demo', 'Demo Plan', 'demo-plan', 'Demo subscription plan',
                    29.99, 299.99, 1000, 10, 100, 10000,
                    '{"unlimited_invoices": true, "ai_processing": true, "multi_currency": true}',
                    1, datetime('now'), datetime('now'), 1
                )
            """))
            dummy_data_created.append("subscription_plan")
        except Exception as e:
            dummy_data_created.append(f"subscription_plan_error: {str(e)}")

        # 2. Create dummy tenant (CORRECTED - matches your model)
        try:
            db.execute(text("""
                INSERT OR IGNORE INTO tenants (
                    id, name, slug, domain, subdomain, plan_id, stripe_customer_id,
                    data_region, compliance_requirements, settings, onboarding_completed,
                    trial_ends_at, subscription_status, is_active,
                    created_at, updated_at, deleted_at, schema_version
                ) VALUES (
                    'demo-tenant-id', 'Demo Company LLC', 'demo-company', 'demo.vritti.ai', 'demo',
                    'plan-demo', 'cus_demo_12345',
                    'us-east', '["SOC2", "GDPR"]', '{"currency": "USD", "timezone": "America/New_York"}', 
                    1, NULL, 'active', 1,
                    datetime('now'), datetime('now'), NULL, 1
                )
            """))
            dummy_data_created.append("tenant")
        except Exception as e:
            dummy_data_created.append(f"tenant_error: {str(e)}")

        # 3. Create dummy tenant users (CORRECTED - matches your model)
        try:
            users_data = [
                ('demo-user-admin', 'demo-tenant-id', 'admin@demo.vritti.ai', None, 'Demo', 'Admin',
                 'admin', '["invoice.read", "invoice.approve", "user.manage"]', 1, 1),
                ('demo-user-acc', 'demo-tenant-id', 'accountant@demo.vritti.ai', None, 'Account', 'Manager',
                 'manager', '["invoice.read", "invoice.approve"]', 1, 1),
                ('demo-user-view', 'demo-tenant-id', 'viewer@demo.vritti.ai', None, 'View', 'Only',
                 'viewer', '["invoice.read"]', 1, 1)
            ]

            for user_data in users_data:
                db.execute(text("""
                    INSERT OR IGNORE INTO tenant_users (
                        id, tenant_id, email, password_hash, first_name, last_name,
                        role, permissions, is_active, email_verified,
                        last_login, login_attempts, created_at, updated_at, schema_version
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        datetime('now'), 0, datetime('now'), datetime('now'), 1
                    )
                """), user_data)
            dummy_data_created.append("tenant_users")
        except Exception as e:
            dummy_data_created.append(f"tenant_users_error: {str(e)}")

        # 4. Create dummy documents (CORRECTED - matches your model)
        try:
            documents_data = [
                ('doc-001', 'demo-tenant-id', 'demo-user-admin', 'RSMA_Invoice.pdf', 'RSMA_Invoice_original.pdf',
                 'pdf', 125432, 'abc123hash', '/gcs/bucket/doc-001.pdf', 'completed', 0.95, 1500),
                ('doc-002', 'demo-tenant-id', 'demo-user-acc', 'Office_Supplies.pdf', 'Office_Supplies_original.pdf',
                 'pdf', 98765, 'def456hash', '/gcs/bucket/doc-002.pdf', 'completed', 0.88, 2200),
                ('doc-003', 'demo-tenant-id', 'demo-user-admin', 'Utility_Bill.jpg', 'Utility_Bill_original.jpg',
                 'jpg', 234567, 'ghi789hash', '/gcs/bucket/doc-003.jpg', 'processing', 0.76, 1800)
            ]

            for doc_data in documents_data:
                db.execute(text("""
                    INSERT OR IGNORE INTO documents (
                        id, tenant_id, uploaded_by, filename, original_filename,
                        file_type, file_size, file_hash, gcs_path, processing_status,
                        confidence_score, processing_time_ms, retry_count,
                        created_at, updated_at, schema_version
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0,
                        datetime('now'), datetime('now'), 1
                    )
                """), doc_data)
            dummy_data_created.append("documents")
        except Exception as e:
            dummy_data_created.append(f"documents_error: {str(e)}")

        # 5. Create dummy invoices (CORRECTED - matches your model)
        try:
            invoices_data = [
                ('inv-001', 'demo-tenant-id', 'doc-001', 'INV-2025-001', 'BLACKBAUD TUITION MANAGEMENT',
                 '123 Education St, Los Angeles, CA 90054', 'TAX123456', '2025-07-01', '2025-07-31',
                 100.00, 8.50, 'USD', 'pending', 'unpaid', 'demo-user-admin'),
                ('inv-002', 'demo-tenant-id', 'doc-002', 'INV-2025-002', 'Office Depot Inc',
                 '456 Supply Ave, New York, NY 10001', 'TAX789012', '2025-07-05', '2025-08-05',
                 250.75, 20.06, 'USD', 'approved', 'paid', 'demo-user-admin'),
                ('inv-003', 'demo-tenant-id', 'doc-003', 'UTIL-2025-003', 'ConEd Utilities',
                 '789 Power Blvd, New York, NY 10002', 'TAX345678', '2025-07-10', '2025-08-10',
                 189.99, 15.20, 'USD', 'pending', 'unpaid', None)
            ]

            for inv_data in invoices_data:
                db.execute(text("""
                    INSERT OR IGNORE INTO invoices (
                        id, tenant_id, document_id, invoice_number, vendor_name,
                        vendor_address, vendor_tax_id, invoice_date, due_date,
                        total_amount, tax_amount, currency, approval_status, payment_status,
                        approved_by, line_items, tags, notes,
                        created_at, updated_at, schema_version
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        '[]', '["office", "recurring"]', 'Demo invoice data',
                        datetime('now'), datetime('now'), 1
                    )
                """), inv_data)
            dummy_data_created.append("invoices")
        except Exception as e:
            dummy_data_created.append(f"invoices_error: {str(e)}")

        # 6. Create dummy tenant usage (CORRECTED)
        try:
            db.execute(text("""
                INSERT OR IGNORE INTO tenant_usage (
                    id, tenant_id, period_start, period_end, documents_processed,
                    api_calls, storage_used_gb, processing_time_minutes, overage_charges,
                    created_at, schema_version
                ) VALUES (
                    'usage-demo-202507', 'demo-tenant-id', 
                    datetime('2025-07-01'), datetime('2025-07-31'),
                    15, 1250, 4.5, 125, 0.0,
                    datetime('now'), 1
                )
            """))
            dummy_data_created.append("tenant_usage")
        except Exception as e:
            dummy_data_created.append(f"tenant_usage_error: {str(e)}")

        # 7. Create dummy audit logs (CORRECTED)
        try:
            audit_data = [
                ('audit-001', 'demo-tenant-id', 'demo-user-admin', 'invoice.created', 'invoice', 'inv-001',
                 '192.168.1.100'),
                ('audit-002', 'demo-tenant-id', 'demo-user-admin', 'invoice.approved', 'invoice', 'inv-002',
                 '192.168.1.100'),
                ('audit-003', 'demo-tenant-id', 'demo-user-acc', 'document.uploaded', 'document', 'doc-003',
                 '192.168.1.101')
            ]

            for audit in audit_data:
                db.execute(text("""
                    INSERT OR IGNORE INTO audit_logs (
                        id, tenant_id, user_id, action, resource_type, resource_id,
                        ip_address, user_agent, old_values, new_values, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, 
                        'Mozilla/5.0 (Demo Browser)', '{}', '{}', datetime('now')
                    )
                """), audit)
            dummy_data_created.append("audit_logs")
        except Exception as e:
            dummy_data_created.append(f"audit_logs_error: {str(e)}")

        # 8. Create dummy tenant API keys (CORRECTED)
        try:
            db.execute(text("""
                INSERT OR IGNORE INTO tenant_api_keys (
                    id, tenant_id, name, key_prefix, key_hash, permissions,
                    last_used, usage_count, is_active, created_at, updated_at, schema_version
                ) VALUES (
                    'api-key-demo', 'demo-tenant-id', 'Demo API Key', 'vrt_test_',
                    'hashed_key_12345', '["documents.read", "invoices.write"]',
                    datetime('now'), 42, 1, datetime('now'), datetime('now'), 1
                )
            """))
            dummy_data_created.append("tenant_api_keys")
        except Exception as e:
            dummy_data_created.append(f"tenant_api_keys_error: {str(e)}")

        # 9. Create dummy webhook endpoints (CORRECTED)
        try:
            db.execute(text("""
                INSERT OR IGNORE INTO webhook_endpoints (
                    id, tenant_id, url, events, secret_hash, is_active,
                    last_success, failure_count, created_at, updated_at, schema_version
                ) VALUES (
                    'webhook-demo', 'demo-tenant-id', 'https://demo.vritti.ai/webhook',
                    '["invoice.processed", "document.uploaded"]', 'secret_hash_demo',
                    1, datetime('now'), 0, datetime('now'), datetime('now'), 1
                )
            """))
            dummy_data_created.append("webhook_endpoints")
        except Exception as e:
            dummy_data_created.append(f"webhook_endpoints_error: {str(e)}")

        # Commit all changes
        db.commit()

        return {
            "status": "success",
            "message": "Corrected dummy data creation completed",
            "created_tables": dummy_data_created,
            "total_operations": len(dummy_data_created),
            "note": "Data structure matches actual SQLAlchemy models"
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/debug/data-summary")
async def get_data_summary(db: Session = Depends(get_db)):
    """Get summary of all data in the database"""
    try:
        summary = {}

        # List of tables to check
        tables = ['tenants', 'tenant_users', 'subscription_plans', 'documents',
                  'invoices', 'tenant_usage', 'audit_logs', 'tenant_api_keys', 'webhook_endpoints']

        for table in tables:
            try:
                # Get count
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {table};")).scalar()

                # Get sample data
                sample_result = db.execute(text(f"SELECT * FROM {table} LIMIT 3;")).fetchall()

                summary[table] = {
                    "count": count_result,
                    "sample_data": [dict(zip([col.name for col in
                                              db.execute(text(f"SELECT * FROM {table} LIMIT 1;")).cursor.description],
                                             row)) for row in sample_result] if sample_result else []
                }

            except Exception as e:
                summary[table] = {"error": str(e)}

        return {
            "status": "success",
            "summary": summary
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/debug/database")
async def debug_database(db: Session = Depends(get_db)):
    """Debug endpoint to check database contents"""
    try:
        # Check if Invoice model exists
        try:
            from src.services.invoice_service import InvoiceService

            # Use the invoice service to check data
            service = InvoiceService(db, "demo-tenant-id")
            recent_invoices = service.get_recent_invoices(10)

            invoices_data = []
            for invoice in recent_invoices:
                invoices_data.append({
                    "id": invoice.id,
                    "vendor_name": invoice.vendor_name,
                    "total_amount": float(invoice.total_amount) if invoice.total_amount else None,
                    "invoice_number": invoice.invoice_number,
                    "created_at": invoice.created_at.isoformat() if invoice.created_at else None
                })

            return {
                "status": "success",
                "total_invoices": len(recent_invoices),
                "recent_invoices": invoices_data,
                "database_connected": True,
                "service_available": True
            }

        except ImportError as e:
            return {
                "status": "error",
                "message": f"Invoice service not found: {str(e)}",
                "database_connected": False
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "database_connected": False
        }


@router.get("/debug/table-structure")
async def debug_table_structure(db: Session = Depends(get_db)):
    """Check the actual structure of tables"""
    try:
        # Check tenants table structure
        tenants_info = db.execute(text("PRAGMA table_info(tenants);")).fetchall()

        # Check tenant_users table structure
        users_info = db.execute(text("PRAGMA table_info(tenant_users);")).fetchall()

        return {
            "status": "success",
            "tenants_columns": [
                {"name": row[1], "type": row[2], "nullable": not row[3], "default": row[4]}
                for row in tenants_info
            ],
            "tenant_users_columns": [
                {"name": row[1], "type": row[2], "nullable": not row[3], "default": row[4]}
                for row in users_info
            ]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/debug/tables")
async def debug_tables(db: Session = Depends(get_db)):
    """Check what tables exist in database"""
    try:
        # Get table names (SQLite specific) - Fixed syntax
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result.fetchall()]

        return {
            "status": "success",
            "tables": tables,
            "database_type": "sqlite"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/debug/create-demo-tenant-fixed")
async def create_demo_tenant_fixed(db: Session = Depends(get_db)):
    """Create demo tenant with correct column mapping"""
    try:
        # First check if demo tenant exists
        existing_check = db.execute(
            text("SELECT id FROM tenants WHERE id = :tenant_id;"),
            {"tenant_id": "demo-tenant-id"}
        ).fetchone()

        if existing_check:
            return {
                "status": "exists",
                "message": "Demo tenant already exists",
                "tenant_id": "demo-tenant-id"
            }

        # Insert tenant with actual column names (based on error message)
        db.execute(text("""
            INSERT INTO tenants (
                id, name, slug, domain, subdomain, 
                plan_id, stripe_customer_id, data_region, compliance_requirements,
                settings, onboarding_completed, trial_ends_at, subscription_status,
                deleted_at, schema_version
            ) VALUES (
                :id, :name, :slug, :domain, :subdomain,
                :plan_id, :stripe_customer_id, :data_region, :compliance_requirements,
                :settings, :onboarding_completed, :trial_ends_at, :subscription_status,
                :deleted_at, :schema_version
            )
        """), {
            "id": "demo-tenant-id",
            "name": "Demo Tenant",
            "slug": "demo-tenant",
            "domain": "demo.vritti.ai",
            "subdomain": None,
            "plan_id": "124",
            "stripe_customer_id": None,
            "data_region": "us-east",
            "compliance_requirements": "{}",
            "settings": "{}",
            "onboarding_completed": True,
            "trial_ends_at": None,
            "subscription_status": "trial",
            "deleted_at": None,
            "schema_version": 1
        })

        # Insert user (check tenant_users structure first)
        db.execute(text("""
            INSERT INTO tenant_users (
                id, tenant_id, email, first_name, last_name, is_active
            ) VALUES (
                :id, :tenant_id, :email, :first_name, :last_name, :is_active
            )
        """), {
            "id": "demo-user-id",
            "tenant_id": "demo-tenant-id",
            "email": "admin@demo.vritti.ai",
            "first_name": "Demo",
            "last_name": "Admin",
            "is_active": True
        })

        db.commit()

        return {
            "status": "created",
            "message": "Demo tenant and user created successfully",
            "tenant_id": "demo-tenant-id",
            "user_id": "demo-user-id"
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/debug/create-demo-invoice")
async def create_demo_invoice(db: Session = Depends(get_db)):
    """Create a demo invoice for testing"""
    try:
        # Insert a demo invoice
        db.execute(text("""
            INSERT INTO invoices (
                id, tenant_id, vendor_name, total_amount, 
                invoice_number, invoice_date, created_at
            ) VALUES (
                :id, :tenant_id, :vendor_name, :total_amount,
                :invoice_number, :invoice_date, :created_at
            )
        """), {
            "id": "demo-invoice-id",
            "tenant_id": "demo-tenant-id",
            "vendor_name": "BLACKBAUD TUITION MANAGEMENT",
            "total_amount": 100.00,
            "invoice_number": "INV-001",
            "invoice_date": "2025-07-14",
            "created_at": "2025-07-14 21:00:00"
        })

        db.commit()

        return {
            "status": "created",
            "message": "Demo invoice created",
            "invoice_id": "demo-invoice-id"
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }


# Add these debugging endpoints to check what's happening:

@router.get("/debug/check-tenant-direct")
async def check_tenant_direct(db: Session = Depends(get_db)):
    """Check if demo tenant exists in database directly"""
    try:
        # Direct SQL check
        result = db.execute(
            text("SELECT id, name, slug, is_active, deleted_at FROM tenants WHERE id = 'demo-tenant-id';")
        ).fetchone()

        if result:
            return {
                "status": "found",
                "tenant_data": {
                    "id": result[0],
                    "name": result[1],
                    "slug": result[2],
                    "is_active": result[3],
                    "deleted_at": result[4]
                }
            }
        else:
            return {
                "status": "not_found",
                "message": "Tenant demo-tenant-id does not exist"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/debug/invoice-service-validation")
async def debug_invoice_service_validation(db: Session = Depends(get_db)):
    """Debug exactly what InvoiceService validation is doing"""
    try:
        # Try to replicate the InvoiceService validation logic
        from src.models.tenant import Tenant

        tenant = db.query(Tenant).filter(
            Tenant.id == "demo-tenant-id",
            Tenant.is_active == True,
            Tenant.deleted_at.is_(None)
        ).first()

        if tenant:
            return {
                "status": "validation_passed",
                "tenant_found": True,
                "tenant_details": {
                    "id": tenant.id,
                    "name": tenant.name,
                    "is_active": tenant.is_active,
                    "deleted_at": tenant.deleted_at,
                    "subscription_status": getattr(tenant, 'subscription_status', 'not_set')
                }
            }
        else:
            # Check what's actually in the database
            all_tenants = db.query(Tenant).all()
            return {
                "status": "validation_failed",
                "tenant_found": False,
                "all_tenants_in_db": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "is_active": t.is_active,
                        "deleted_at": t.deleted_at
                    } for t in all_tenants
                ]
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }


@router.post("/debug/create-simple-tenant")
async def create_simple_tenant(db: Session = Depends(get_db)):
    """Create tenant using SQLAlchemy models directly"""
    try:
        from src.models.tenant import Tenant, SubscriptionPlan

        # Check if tenant already exists
        existing = db.query(Tenant).filter(Tenant.id == "demo-tenant-id").first()
        if existing:
            return {
                "status": "already_exists",
                "tenant_id": existing.id,
                "name": existing.name
            }

        # Make sure subscription plan exists
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == "plan-demo").first()
        if not plan:
            # Create simple plan
            plan = SubscriptionPlan(
                id="plan-demo",
                name="Demo Plan",
                slug="demo-plan",
                is_active=True
            )
            db.add(plan)
            db.flush()  # Get the ID

        # Create tenant using SQLAlchemy model
        tenant = Tenant(
            id="demo-tenant-id",
            name="Demo Company LLC",
            slug="demo-company",
            domain="demo.vritti.ai",
            plan_id=plan.id,
            data_region="us-east",
            subscription_status="active",
            is_active=True
        )

        db.add(tenant)
        db.commit()

        return {
            "status": "created",
            "tenant_id": tenant.id,
            "name": tenant.name,
            "plan_id": tenant.plan_id
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }


@router.post("/debug/cleanup-and-create")
async def cleanup_and_create_tenant(db: Session = Depends(get_db)):
    """Clean up existing data and create fresh demo tenant"""
    try:
        from src.models.tenant import Tenant, SubscriptionPlan

        # Delete all existing tenants to start fresh
        db.query(Tenant).delete()

        # Delete existing plans
        db.query(SubscriptionPlan).delete()

        db.flush()

        # Create new subscription plan
        plan = SubscriptionPlan(
            id="plan-demo",
            name="Demo Plan",
            slug="demo-plan",
            is_active=True
        )
        db.add(plan)
        db.flush()

        # Create new tenant
        tenant = Tenant(
            id="demo-tenant-id",
            name="Demo Company LLC",
            slug="demo-company",
            domain="demo.vritti.ai",
            plan_id=plan.id,
            data_region="us-east",
            subscription_status="active",
            is_active=True
        )

        db.add(tenant)
        db.commit()

        return {
            "status": "created_fresh",
            "tenant_id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "cleanup_performed": True
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }


# Add this debug endpoint to your src/api/v1/conversation.py

# Add this FIXED debug endpoint to your src/api/v1/conversation.py

@router.get("/debug/ask-vritti-context")
async def debug_ask_vritti_context(db: Session = Depends(get_db)):
    """Debug what context Ask Vritti is actually using"""
    try:
        # Import the Invoice model
        from src.models.tenant import Invoice
        from src.services.invoice_service import InvoiceService

        # Test the exact path that Ask Vritti uses
        demo_tenant_id = "demo-tenant-id"
        demo_user_id = "demo-user-id"

        # Simulate what Ask Vritti's _handle_search_invoices does
        invoices_query = db.query(Invoice).filter(
            Invoice.tenant_id == demo_tenant_id,
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.created_at.desc()).limit(10).all()

        # Check pending invoices (for greeting)
        pending_query = db.query(Invoice).filter(
            Invoice.tenant_id == demo_tenant_id,
            Invoice.approval_status == 'pending',
            Invoice.deleted_at.is_(None)
        ).count()

        # Test InvoiceService for comparison
        invoice_service = InvoiceService(db, demo_tenant_id)
        service_invoices = invoice_service.get_recent_invoices(10)
        service_pending = invoice_service.get_pending_approvals(10)

        # Check raw database for comparison
        raw_invoices = db.execute(text("""
            SELECT tenant_id, vendor_name, total_amount, approval_status 
            FROM invoices 
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
        """)).fetchall()

        return {
            "ask_vritti_simulation": {
                "tenant_id_used": demo_tenant_id,
                "user_id_used": demo_user_id,
                "direct_query_found": len(invoices_query),
                "pending_count": pending_query,
                "invoice_details": [
                    {
                        "vendor": inv.vendor_name,
                        "amount": float(inv.total_amount) if inv.total_amount else 0,
                        "status": inv.approval_status,
                        "tenant_id": inv.tenant_id
                    }
                    for inv in invoices_query
                ]
            },
            "invoice_service_test": {
                "recent_invoices_found": len(service_invoices),
                "pending_invoices_found": len(service_pending),
                "service_results": [
                    {
                        "vendor": inv.vendor_name,
                        "amount": float(inv.total_amount) if inv.total_amount else 0,
                        "status": inv.approval_status
                    }
                    for inv in service_invoices
                ]
            },
            "raw_database_check": [
                {
                    "tenant_id": row[0],
                    "vendor_name": row[1],
                    "total_amount": row[2],
                    "approval_status": row[3]
                }
                for row in raw_invoices
            ],
            "diagnosis": {
                "total_invoices_in_db": len(raw_invoices),
                "ask_vritti_direct_query": len(invoices_query),
                "invoice_service_finds": len(service_invoices),
                "problem_identified": len(invoices_query) == 0 and len(raw_invoices) > 0,
                "recommendation": "Check tenant_id matching in Ask Vritti context"
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }


# Add this test endpoint to your src/api/v1/conversation.py

@router.post("/debug/test-ask-vritti-direct")
async def test_ask_vritti_direct(
        test_message: str = "Show me pending invoices",
        db: Session = Depends(get_db)
):
    """Test Ask Vritti AI agent directly with debugging"""
    try:
        # Create a test context exactly like the real chat
        if not ask_vritti:
            return {"error": "Ask Vritti not initialized"}

        session_id = f"debug-{uuid.uuid4()}"
        demo_tenant_id = "demo-tenant-id"
        demo_user_id = "demo-user-id"

        # Create context exactly like real chat
        context = ask_vritti.create_conversation_context(
            session_id=session_id,
            tenant_id=demo_tenant_id,
            user_id=demo_user_id
        )

        # Test intent classification
        intent = ask_vritti.classify_intent(test_message)

        # Test entity extraction
        entities = ask_vritti.extract_entities(test_message)

        # Test the full message processing
        ai_response = await ask_vritti.process_message(test_message, context)

        return {
            "test_input": test_message,
            "debug_info": {
                "session_id": session_id,
                "tenant_id": demo_tenant_id,
                "user_id": demo_user_id,
                "classified_intent": intent.value,
                "extracted_entities": {
                    "vendor_name": entities.vendor_name,
                    "amount": entities.amount,
                    "invoice_number": entities.invoice_number
                }
            },
            "ai_response": {
                "text": ai_response.text,
                "intent": ai_response.intent.value,
                "action_required": ai_response.action_required,
                "llm_used": ai_response.llm_used.value if ai_response.llm_used else None,
                "cost": ai_response.cost,
                "confidence": ai_response.confidence
            },
            "context_after": {
                "total_cost": context.total_cost,
                "conversation_history_length": len(context.conversation_history)
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }

@router.get("/debug/raw-count")
async def debug_raw_count(db: Session = Depends(get_db)):
    """Get raw count of records in database"""
    try:
        # Try to count invoices using raw SQL
        result = db.execute(text("SELECT COUNT(*) FROM invoices;"))
        count = result.scalar()

        # Also get some sample data
        result = db.execute(text("SELECT vendor_name, total_amount, created_at FROM invoices LIMIT 5;"))
        samples = result.fetchall()

        return {
            "status": "success",
            "total_count": count,
            "sample_data": [
                {
                    "vendor_name": row[0],
                    "total_amount": row[1],
                    "created_at": row[2]
                } for row in samples
            ]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Rest of your endpoints remain the same...