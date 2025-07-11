# 🏗️ Vritti Technical Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Mobile Web UI       │  Admin Dashboard     │  Customer Portal      │
│                      │  (Streamlit)         │  (Phase 2)            │
│ • Camera Capture     │ • Tenant Mgmt        │ • Self-Service        │
│ • Conversational AI  │ • Analytics          │ • Billing Portal      │
│ • Voice Commands     │ • User Management    │ • Usage Reports       │
│ • Approval Workflow  │ • System Health      │                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────┐
│                    API LAYER                                        │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Backend     │  Authentication      │  Integration Hub      │
│                      │                      │                       │
│ • Invoice Processing │ • JWT Multi-tenant   │ • QuickBooks API      │
│ • Conversational AI  │ • RBAC System        │ • Webhook Handler     │
│ • File Upload        │ • Session Mgmt       │ • Third-party APIs    │
│ • Approval Workflows │ • Security Middleware│ • Event System       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│  AI Processing       │  Workflow Engine     │  Integration Services │
│                      │                      │                       │
│ • Document AI        │ • Approval Rules     │ • QB Sync Manager     │
│ • Conversational AI  │ • Notifications      │ • Data Transformation │
│ • Confidence Scoring │ • Audit Logging      │ • Error Handling      │
│ • Pattern Detection  │ • Business Rules     │ • Retry Logic         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                       │
├─────────────────────────────────────────────────────────────────────┤
│  PostgreSQL Database │  Redis Cache         │  Cloud Storage        │
│                      │                      │                       │
│ • Multi-tenant Data  │ • Session Store      │ • Invoice Files       │
│ • User Management    │ • Chat History       │ • AI Processing Cache │
│ • Audit Trails       │ • Processing Queue   │ • Backup Archives     │
│ • Integration Logs   │ • Rate Limiting      │ • Static Assets       │
└─────────────────────────────────────────────────────────────────────┘
```

## GCP Infrastructure Architecture

### Core Services
```
Vritti GCP Deployment:
├── 🚀 Cloud Run
│   ├── vritti-api (Backend API)
│   ├── vritti-mobile-ui (Mobile Web App)
│   └── vritti-admin (Admin Dashboard)
├── 🗄️ Cloud SQL PostgreSQL
│   ├── Multi-tenant database
│   ├── Automated backups
│   └── High availability setup
├── 🤖 AI Services
│   ├── Document AI (Invoice processing)
│   ├── Vertex AI (Gemini Pro for conversations)
│   └── Vision API (Image enhancement)
├── 💾 Storage Services
│   ├── Cloud Storage (Files & assets)
│   ├── Cloud KMS (Encryption keys)
│   └── Secret Manager (API keys)
├── 🔒 Security & Monitoring
│   ├── Cloud IAM (Access control)
│   ├── Cloud Monitoring (Observability)
│   ├── Cloud Logging (Audit trails)
│   └── Cloud Armor (DDoS protection)
└── 🔄 DevOps
    ├── Cloud Build (CI/CD)
    ├── Container Registry (Docker images)
    └── Cloud Deploy (Deployment automation)
```

## Database Schema

### Core Tables
```sql
-- Multi-tenant foundation
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(100) UNIQUE,
    admin_email VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- User management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Invoice processing
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255),
    file_url VARCHAR(500),
    status VARCHAR(50) DEFAULT 'processing',
    extracted_data JSONB,
    confidence_scores JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- Conversational AI history
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    invoice_id UUID REFERENCES invoices(id),
    message_type VARCHAR(20), -- 'user' or 'assistant'
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- QuickBooks integration
CREATE TABLE quickbooks_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    company_id VARCHAR(100),
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    last_sync TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit logging
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## API Architecture

### FastAPI Application Structure
```python
# main.py - Application entry point
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from middleware.tenant import TenantMiddleware
from middleware.auth import AuthMiddleware
from routes import invoices, auth, quickbooks, conversations

app = FastAPI(title="Vritti API", version="1.0.0")

# Middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(TenantMiddleware)
app.add_middleware(AuthMiddleware)

# Routes
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(invoices.router, prefix="/api/v1/invoices")
app.include_router(conversations.router, prefix="/api/v1/conversations")
app.include_router(quickbooks.router, prefix="/api/v1/quickbooks")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "vritti-api"}
```

### Key API Endpoints
```python
# Authentication & Tenant Management
POST /api/v1/auth/register          # Tenant & user registration
POST /api/v1/auth/login             # User authentication
POST /api/v1/auth/refresh           # Token refresh
GET  /api/v1/auth/me                # Current user info

# Invoice Processing
POST /api/v1/invoices/upload        # Upload & process invoice
GET  /api/v1/invoices               # List tenant invoices
GET  /api/v1/invoices/{id}          # Get invoice details
PUT  /api/v1/invoices/{id}/approve  # Approve invoice
DELETE /api/v1/invoices/{id}        # Delete invoice

# Conversational AI
POST /api/v1/conversations/chat     # Chat with AI about invoices
GET  /api/v1/conversations/history  # Chat history
POST /api/v1/conversations/clear    # Clear conversation

# QuickBooks Integration
GET  /api/v1/quickbooks/auth-url    # Get OAuth URL
POST /api/v1/quickbooks/callback    # OAuth callback
GET  /api/v1/quickbooks/status      # Connection status
POST /api/v1/quickbooks/sync        # Manual sync trigger
GET  /api/v1/quickbooks/companies   # List QB companies
```

## Mobile Web UI Architecture

### React Application Structure
```
mobile-ui/
├── src/
│   ├── components/
│   │   ├── CameraCapture.tsx       # Camera invoice scanning
│   │   ├── ConversationalChat.tsx  # AI chat interface
│   │   ├── InvoiceProcessor.tsx    # Processing workflow
│   │   ├── ApprovalWorkflow.tsx    # Mobile approval UI
│   │   └── QuickBooksSync.tsx      # QB integration status
│   ├── pages/
│   │   ├── Dashboard.tsx           # Main mobile dashboard
│   │   ├── Upload.tsx              # Upload interface
│   │   ├── Chat.tsx                # Conversation page
│   │   ├── Invoices.tsx            # Invoice list
│   │   └── Settings.tsx            # User settings
│   ├── hooks/
│   │   ├── useCamera.ts            # Camera functionality
│   │   ├── useConversation.ts      # Chat management
│   │   ├── useInvoices.ts          # Invoice operations
│   │   └── useAuth.ts              # Authentication
│   ├── services/
│   │   ├── api.ts                  # API client
│   │   ├── auth.ts                 # Auth service
│   │   └── storage.ts              # Local storage
│   └── utils/
│       ├── camera.ts               # Camera utilities
│       ├── validation.ts           # Form validation
│       └── formatting.ts           # Data formatting
```

### PWA Features
```json
// manifest.json - Progressive Web App config
{
  "name": "Vritti AI Invoice Assistant",
  "short_name": "Vritti",
  "description": "AI-powered invoice processing",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#4F46E5",
  "background_color": "#FFFFFF",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ],
  "capabilities": ["camera", "microphone"],
  "categories": ["business", "finance", "productivity"]
}
```

## AI System Architecture

### Conversational AI Pipeline
```python
# agents/vritti_agent.py
class VrittiAgent:
    def __init__(self):
        self.llm = ChatVertexAI(
            model_name="gemini-pro",
            temperature=0.1,
            project=GCP_PROJECT_ID
        )
        self.tools = [
            InvoiceProcessingTool(),
            InvoiceSearchTool(),
            QuickBooksSyncTool(),
            AnalyticsTool()
        ]
        
    async def process_conversation(self, message: str, context: dict):
        # Tenant-aware processing
        tenant_id = context.get("tenant_id")
        user_id = context.get("user_id")
        
        # Generate response with business context
        response = await self.agent_executor.ainvoke({
            "input": message,
            "tenant_id": tenant_id,
            "chat_history": context.get("history", [])
        })
        
        return response
```

### Document Processing Pipeline
```python
# services/document_processing.py
class DocumentProcessor:
    def __init__(self):
        self.document_ai_client = DocumentAIClient()
        self.storage_client = StorageClient()
        
    async def process_invoice(self, file: UploadFile, tenant_id: str):
        # 1. Upload to Cloud Storage
        file_url = await self.storage_client.upload(file, tenant_id)
        
        # 2. Process with Document AI
        extraction_result = await self.document_ai_client.process(file_url)
        
        # 3. Apply business rules validation
        validated_data = self.validate_extraction(extraction_result)
        
        # 4. Store results in database
        invoice = await self.store_invoice(validated_data, tenant_id)
        
        return invoice
```

## Security Architecture

### Multi-Tenant Security
```python
# middleware/tenant.py
class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract tenant context from JWT
        token = request.headers.get("Authorization")
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.state.tenant_id = payload.get("tenant_id")
            request.state.user_id = payload.get("user_id")
        
        response = await call_next(request)
        return response

# Data isolation at query level
class TenantAwareQuery:
    @staticmethod
    def filter_by_tenant(query, tenant_id: str):
        return query.filter(model.tenant_id == tenant_id)
```

### Encryption & Security
```python
# security/encryption.py
class VrittiEncryption:
    def __init__(self):
        self.kms_client = kms.KeyManagementServiceClient()
        self.key_name = f"projects/{GCP_PROJECT}/locations/global/keyRings/vritti/cryptoKeys/tenant-data"
    
    def encrypt_sensitive_data(self, data: str, tenant_id: str) -> str:
        # Tenant-specific encryption
        key_version = f"{self.key_name}/cryptoKeyVersions/1"
        encrypted = self.kms_client.encrypt(
            request={"name": key_version, "plaintext": data.encode()}
        )
        return base64.b64encode(encrypted.ciphertext).decode()
```

## Performance & Scaling

### Caching Strategy
```python
# services/cache.py
class VrittiCache:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(REDIS_URL)
    
    async def cache_conversation(self, tenant_id: str, user_id: str, conversation: dict):
        key = f"conversation:{tenant_id}:{user_id}"
        await self.redis_client.setex(key, 3600, json.dumps(conversation))
    
    async def cache_invoice_results(self, invoice_id: str, results: dict):
        key = f"invoice:{invoice_id}:results"
        await self.redis_client.setex(key, 7200, json.dumps(results))
```

### Database Optimization
```sql
-- Performance indexes
CREATE INDEX idx_invoices_tenant_created ON invoices(tenant_id, created_at DESC);
CREATE INDEX idx_conversations_tenant_user ON conversations(tenant_id, user_id, created_at DESC);
CREATE INDEX idx_audit_logs_tenant_action ON audit_logs(tenant_id, action, created_at DESC);
CREATE INDEX idx_users_tenant_email ON users(tenant_id, email);

-- Partitioning for large datasets
CREATE TABLE audit_logs_2024 PARTITION OF audit_logs 
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## Monitoring & Observability

### Health Checks
```python
# monitoring/health.py
@app.get("/health/detailed")
async def detailed_health_check():
    checks = {
        "database": await check_database_connection(),
        "redis": await check_redis_connection(),
        "document_ai": await check_document_ai_service(),
        "vertex_ai": await check_vertex_ai_service(),
        "storage": await check_cloud_storage(),
        "quickbooks": await check_quickbooks_api()
    }
    
    overall_status = "healthy" if all(checks.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": app.version
    }
```

### Metrics Collection
```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
invoices_processed = Counter('vritti_invoices_processed_total', 
                           'Total invoices processed', ['tenant_id', 'status'])
processing_duration = Histogram('vritti_processing_duration_seconds',
                               'Invoice processing duration')
active_conversations = Gauge('vritti_active_conversations',
                           'Number of active conversations')

# System metrics
api_requests = Counter('vritti_api_requests_total',
                      'Total API requests', ['method', 'endpoint', 'status'])
database_connections = Gauge('vritti_db_connections_active',
                            'Active database connections')
```

This technical architecture provides the foundation for building Vritti as a scalable, secure, and maintainable SaaS platform on GCP.