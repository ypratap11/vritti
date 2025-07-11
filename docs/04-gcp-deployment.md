# ☁️ Vritti GCP Deployment Guide

## GCP Project Setup

### Initial Project Configuration
```bash
# Create Vritti GCP project
gcloud projects create vritti-ai-prod --name="Vritti AI Platform"
gcloud config set project vritti-ai-prod

# Link billing account (required for APIs)
gcloud billing projects link vritti-ai-prod \
  --billing-account=BILLING_ACCOUNT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  documentai.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  iam.googleapis.com
```

### Service Account Setup
```bash
# Create service accounts for different services
gcloud iam service-accounts create vritti-api-sa \
  --display-name="Vritti API Service Account" \
  --description="Service account for Vritti API on Cloud Run"

gcloud iam service-accounts create vritti-build-sa \
  --display-name="Vritti Build Service Account" \
  --description="Service account for Cloud Build deployments"

# Grant necessary permissions
gcloud projects add-iam-policy-binding vritti-ai-prod \
  --member="serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com" \
  --role="roles/documentai.apiUser"

gcloud projects add-iam-policy-binding vritti-ai-prod \
  --member="serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding vritti-ai-prod \
  --member="serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## Database Configuration

### Cloud SQL PostgreSQL Setup
```bash
# Create production database instance
gcloud sql instances create vritti-prod \
  --database-version=POSTGRES_14 \
  --tier=db-custom-2-4096 \
  --region=us-central1 \
  --storage-size=100GB \
  --storage-type=SSD \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=06 \
  --maintenance-release-channel=production \
  --deletion-protection

# Create database and users
gcloud sql databases create vritti --instance=vritti-prod

# Create application user
gcloud sql users create vritti-app \
  --instance=vritti-prod \
  --password=SECURE_PASSWORD_HERE

# Get connection name for Cloud Run
gcloud sql instances describe vritti-prod \
  --format="value(connectionName)"
```

### Database Migration Setup
```sql
-- Initial schema creation
-- Connect to vritti database and run:

-- Multi-tenant foundation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(100) UNIQUE,
    admin_email VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    qb_company_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_tenants_domain ON tenants(domain);
CREATE INDEX idx_users_tenant_email ON users(tenant_id, email);
CREATE INDEX idx_users_tenant_active ON users(tenant_id, is_active);
```

---

## Storage Configuration

### Cloud Storage Buckets
```bash
# Create storage buckets with appropriate lifecycle policies
gsutil mb -l us-central1 gs://vritti-invoices-prod
gsutil mb -l us-central1 gs://vritti-static-assets
gsutil mb -l us-central1 gs://vritti-backups

# Set up bucket permissions
gsutil iam ch serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com:objectAdmin \
  gs://vritti-invoices-prod

gsutil iam ch serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com:objectViewer \
  gs://vritti-static-assets

# Configure lifecycle policies
cat > invoice-lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
        "condition": {"age": 365}
      }
    ]
  }
}
EOF

gsutil lifecycle set invoice-lifecycle.json gs://vritti-invoices-prod
```

---

## Secret Management

### Storing Sensitive Configuration
```bash
# Database connection string
echo -n "postgresql://vritti-app:PASSWORD@/vritti?host=/cloudsql/vritti-ai-prod:us-central1:vritti-prod" | \
  gcloud secrets create vritti-database-url --data-file=-

# JWT secret key
openssl rand -base64 32 | gcloud secrets create vritti-jwt-secret --data-file=-

# QuickBooks OAuth credentials
cat > qb-credentials.json << EOF
{
  "client_id": "QB_CLIENT_ID",
  "client_secret": "QB_CLIENT_SECRET",
  "sandbox_base_url": "https://sandbox-quickbooks.api.intuit.com",
  "discovery_document": "https://appcenter.intuit.com/api/v1/OpenID_OIDC"
}
EOF

gcloud secrets create vritti-quickbooks-credentials --data-file=qb-credentials.json

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding vritti-database-url \
  --member="serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding vritti-jwt-secret \
  --member="serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding vritti-quickbooks-credentials \
  --member="serviceAccount:vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Cloud Run Deployment

### Backend API Deployment
```yaml
# cloudbuild.yaml for CI/CD
steps:
  # Build backend Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/vritti-ai-prod/vritti-api:$BUILD_ID',
      '-t', 'gcr.io/vritti-ai-prod/vritti-api:latest',
      './backend'
    ]

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/vritti-ai-prod/vritti-api:$BUILD_ID']

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', 'vritti-api',
      '--image', 'gcr.io/vritti-ai-prod/vritti-api:$BUILD_ID',
      '--region', 'us-central1',
      '--platform', 'managed',
      '--service-account', 'vritti-api-sa@vritti-ai-prod.iam.gserviceaccount.com',
      '--memory', '4Gi',
      '--cpu', '2',
      '--min-instances', '1',
      '--max-instances', '100',
      '--concurrency', '80',
      '--timeout', '300',
      '--port', '8000',
      '--allow-unauthenticated'
    ]

  # Set environment variables
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'services', 'update', 'vritti-api',
      '--region', 'us-central1',
      '--set-env-vars', 'GCP_PROJECT_ID=vritti-ai-prod,ENVIRONMENT=production',
      '--set-secrets', 'DATABASE_URL=vritti-database-url:latest,JWT_SECRET=vritti-jwt-secret:latest,QB_CREDENTIALS=vritti-quickbooks-credentials:latest'
    ]

options:
  logging: CLOUD_LOGGING_ONLY
```

### Frontend Deployment Configuration
```dockerfile
# mobile-ui/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```bash
# Deploy mobile UI
gcloud run deploy vritti-ui \
  --source=./mobile-ui \
  --region=us-central1 \
  --platform=managed \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=50 \
  --concurrency=100 \
  --port=80 \
  --allow-unauthenticated \
  --set-env-vars="REACT_APP_API_URL=https://vritti-api-xxxxx-uc.a.run.app"
```

---

## Custom Domain & SSL

### Domain Configuration
```bash
# Map custom domain to Cloud Run services
gcloud run domain-mappings create \
  --service=vritti-api \
  --domain=api.vritti.ai \
  --region=us-central1

gcloud run domain-mappings create \
  --service=vritti-ui \
  --domain=app.vritti.ai \
  --region=us-central1

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain=api.vritti.ai \
  --region=us-central1
```

### Load Balancer Setup (Optional)
```bash
# Create global load balancer for better performance
gcloud compute backend-services create vritti-backend \
  --global \
  --protocol=HTTP \
  --port-name=http \
  --health-checks=vritti-health-check

# Add Cloud Run as backend
gcloud compute backend-services add-backend vritti-backend \
  --global \
  --network-endpoint-group=vritti-neg \
  --network-endpoint-group-region=us-central1
```

---

## Monitoring & Observability

### Cloud Monitoring Dashboard
```json
{
  "displayName": "Vritti Production Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "API Request Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"vritti-api\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE",
                    "crossSeriesReducer": "REDUCE_SUM"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Invoice Processing Latency",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_DELTA",
                    "crossSeriesReducer": "REDUCE_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
```

### Alerting Policies
```yaml
# alerting-policies.yaml
displayName: "Vritti Critical Alerts"
conditions:
  - displayName: "High Error Rate"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND resource.labels.service_name="vritti-api"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.05
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_MEAN
  - displayName: "High Response Time"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 5000
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_DELTA
          crossSeriesReducer: REDUCE_PERCENTILE_95

notificationChannels:
  - type: "email"
    labels:
      email_address: "alerts@vritti.ai"
  - type: "slack"
    labels:
      channel_name: "#vritti-alerts"
      webhook_url: "SLACK_WEBHOOK_URL"
```

### Application Performance Monitoring
```python
# backend/monitoring/apm.py
from google.cloud import monitoring_v3
from google.cloud import trace_v1
import time
import functools

class VrittiMonitoring:
    def __init__(self):
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.trace_client = trace_v1.TraceServiceClient()
        self.project_name = f"projects/{os.getenv('GCP_PROJECT_ID')}"
    
    def record_invoice_processing_time(self, duration_ms: float, tenant_id: str):
        """Record invoice processing duration"""
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/vritti/invoice_processing_duration"
        series.resource.type = "global"
        series.metric.labels["tenant_id"] = tenant_id
        
        point = monitoring_v3.Point()
        point.value.double_value = duration_ms
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]
        
        self.monitoring_client.create_time_series(
            name=self.project_name, time_series=[series]
        )
    
    def record_business_metric(self, metric_name: str, value: float, labels: dict):
        """Record custom business metrics"""
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/vritti/{metric_name}"
        series.resource.type = "global"
        
        for key, val in labels.items():
            series.metric.labels[key] = str(val)
        
        point = monitoring_v3.Point()
        point.value.double_value = value
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]
        
        self.monitoring_client.create_time_series(
            name=self.project_name, time_series=[series]
        )

def monitor_performance(metric_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                VrittiMonitoring().record_business_metric(
                    f"{metric_name}_duration",
                    duration,
                    {"success": success, "function": func.__name__}
                )
            return result
        return wrapper
    return decorator
```

---

## Cost Optimization

### Resource Optimization Configuration
```bash
# Configure cost-effective scaling
gcloud run services update vritti-api \
  --region=us-central1 \
  --cpu-throttling \
  --execution-environment=gen2 \
  --memory=2Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80

# Set up budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Vritti Monthly Budget" \
  --budget-amount=500 \
  --threshold-rule=percent-rule,0.8 \
  --threshold-rule=percent-rule,0.9 \
  --threshold-rule=percent-rule,1.0
```

### Cost Monitoring Query
```sql
-- BigQuery cost analysis query
SELECT
  service.description as service,
  location.location as region,
  SUM(cost) as total_cost,
  SUM(usage.amount) as total_usage,
  usage.unit as unit,
  DATE(usage_start_time) as usage_date
FROM `vritti-ai-prod.cloud_billing_export.gcp_billing_export_v1_XXXXXX`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND project.id = 'vritti-ai-prod'
GROUP BY service.description, location.location, usage.unit, usage_date
ORDER BY total_cost DESC;
```

---

## Security Configuration

### IAM & Security Best Practices
```bash
# Create custom roles for fine-grained access
gcloud iam roles create vrittiApiRole \
  --project=vritti-ai-prod \
  --title="Vritti API Service Role" \
  --description="Custom role for Vritti API service" \
  --permissions="documentai.processors.process,aiplatform.endpoints.predict,storage.objects.create,storage.objects.get,secretmanager.versions.access"

# Network security
gcloud compute firewall-rules create vritti-internal-only \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:8080 \
  --source-ranges=10.0.0.0/8 \
  --target-tags=vritti-internal

# Enable audit logging
cat > audit-policy.yaml << EOF
auditConfigs:
- service: allServices
  auditLogConfigs:
  - logType: ADMIN_READ
  - logType: DATA_READ
  - logType: DATA_WRITE
EOF

gcloud logging sinks create vritti-audit-sink \
  bigquery.googleapis.com/projects/vritti-ai-prod/datasets/audit_logs \
  --log-filter='protoPayload.serviceName="cloudsql.googleapis.com" OR protoPayload.serviceName="run.googleapis.com"'
```

### Data Encryption Configuration
```python
# backend/security/encryption.py
from google.cloud import kms
import base64
import os

class VrittiKMSManager:
    def __init__(self):
        self.client = kms.KeyManagementServiceClient()
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.location = 'global'
        self.key_ring = 'vritti-keys'
        self.key_name = 'tenant-data-key'
        
        self.key_path = self.client.crypto_key_path(
            self.project_id, self.location, self.key_ring, self.key_name
        )
    
    def encrypt_tenant_data(self, plaintext: str, tenant_id: str) -> str:
        """Encrypt sensitive tenant data"""
        # Add tenant context to additional data
        additional_data = f"tenant:{tenant_id}".encode()
        
        encrypt_response = self.client.encrypt(
            request={
                "name": self.key_path,
                "plaintext": plaintext.encode(),
                "additional_authenticated_data": additional_data
            }
        )
        
        return base64.b64encode(encrypt_response.ciphertext).decode()
    
    def decrypt_tenant_data(self, ciphertext: str, tenant_id: str) -> str:
        """Decrypt sensitive tenant data"""
        additional_data = f"tenant:{tenant_id}".encode()
        
        decrypt_response = self.client.decrypt(
            request={
                "name": self.key_path,
                "ciphertext": base64.b64decode(ciphertext),
                "additional_authenticated_data": additional_data
            }
        )
        
        return decrypt_response.plaintext.decode()
```

---

## Backup & Disaster Recovery

### Automated Backup Configuration
```bash
# Database backup automation
gcloud sql instances patch vritti-prod \
  --backup-start-time=03:00 \
  --retained-backups-count=30 \
  --retained-transaction-log-days=7

# Cloud Storage backup automation
cat > backup-lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 2555}
      }
    ]
  }
}
EOF

gsutil lifecycle set backup-lifecycle.json gs://vritti-backups
```

### Disaster Recovery Procedures
```python
# scripts/disaster_recovery.py
import subprocess
import datetime
import os

class DisasterRecovery:
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.backup_bucket = 'gs://vritti-backups'
        
    def backup_database(self):
        """Create on-demand database backup"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_id = f"vritti-manual-backup-{timestamp}"
        
        cmd = [
            'gcloud', 'sql', 'backups', 'create',
            '--instance=vritti-prod',
            f'--description=Manual backup {timestamp}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def restore_from_backup(self, backup_id: str, target_instance: str):
        """Restore database from backup"""
        cmd = [
            'gcloud', 'sql', 'backups', 'restore', backup_id,
            '--restore-instance', target_instance,
            '--backup-instance', 'vritti-prod'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def export_tenant_data(self, tenant_id: str):
        """Export specific tenant data for migration"""
        export_file = f"{self.backup_bucket}/tenant-exports/{tenant_id}-{datetime.date.today()}.sql"
        
        cmd = [
            'gcloud', 'sql', 'export', 'sql', 'vritti-prod', export_file,
            '--database=vritti',
            f"--query=SELECT * FROM invoices WHERE tenant_id='{tenant_id}'"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
```

---

## Performance Optimization

### Database Performance Tuning
```sql
-- Performance optimization queries
-- Connection pooling configuration
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- Optimize for SSD storage
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET seq_page_cost = 1.0;

-- Connection pooling for multi-tenant apps
ALTER SYSTEM SET max_prepared_transactions = 100;
ALTER SYSTEM SET max_locks_per_transaction = 256;

-- Additional indexes for performance
CREATE INDEX CONCURRENTLY idx_invoices_tenant_status_created 
  ON invoices(tenant_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY idx_conversations_tenant_invoice_created 
  ON conversations(tenant_id, invoice_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_audit_logs_tenant_action_created 
  ON audit_logs(tenant_id, action, created_at DESC) 
  WHERE created_at >= NOW() - INTERVAL '90 days';

-- Partitioning for large tables
CREATE TABLE audit_logs_current PARTITION OF audit_logs 
  FOR VALUES FROM (CURRENT_DATE) TO (CURRENT_DATE + INTERVAL '1 month');
```

### Cloud Run Performance Configuration
```yaml
# performance-optimized service configuration
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: vritti-api
  annotations:
    run.googleapis.com/execution-environment: gen2
    run.googleapis.com/cpu-throttling: "false"
    autoscaling.knative.dev/maxScale: "100"
    autoscaling.knative.dev/minScale: "2"
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "100"
        run.googleapis.com/memory: "4Gi"
        run.googleapis.com/cpu: "2"
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
      - image: gcr.io/vritti-ai-prod/vritti-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: WORKERS
          value: "4"
        - name: WORKER_CLASS
          value: "uvicorn.workers.UvicornWorker"
        resources:
          limits:
            memory: "4Gi"
            cpu: "2"
```

---

## Development & CI/CD Pipeline

### Cloud Build Configuration
```yaml
# cloudbuild.yaml - Complete CI/CD pipeline
steps:
  # Run tests
  - name: 'python:3.11'
    entrypoint: 'bash'
    args:
    - '-c'
    - |
      cd backend
      pip install -r requirements.txt
      python -m pytest tests/ -v --cov=src/

  # Build and test mobile UI
  - name: 'node:18'
    entrypoint: 'bash'
    args:
    - '-c'
    - |
      cd mobile-ui
      npm ci
      npm run test -- --coverage --watchAll=false
      npm run build

  # Build backend image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/vritti-api:$BUILD_ID',
      '-t', 'gcr.io/$PROJECT_ID/vritti-api:latest',
      './backend'
    ]

  # Build frontend image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/vritti-ui:$BUILD_ID',
      '-t', 'gcr.io/$PROJECT_ID/vritti-ui:latest',
      '--build-arg', 'REACT_APP_API_URL=https://api.vritti.ai',
      './mobile-ui'
    ]

  # Push images
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/vritti-api:$BUILD_ID']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/vritti-ui:$BUILD_ID']

  # Deploy to staging (if branch is develop)
  - name: 'gcr.io/cloud-builders/gcloud'
    entrypoint: 'bash'
    args:
    - '-c'
    - |
      if [ "$BRANCH_NAME" = "develop" ]; then
        gcloud run deploy vritti-api-staging \
          --image gcr.io/$PROJECT_ID/vritti-api:$BUILD_ID \
          --region us-central1 \
          --platform managed \
          --allow-unauthenticated
      fi

  # Deploy to production (if branch is main)
  - name: 'gcr.io/cloud-builders/gcloud'
    entrypoint: 'bash'
    args:
    - '-c'
    - |
      if [ "$BRANCH_NAME" = "main" ]; then
        gcloud run deploy vritti-api \
          --image gcr.io/$PROJECT_ID/vritti-api:$BUILD_ID \
          --region us-central1 \
          --platform managed \
          --allow-unauthenticated
        
        gcloud run deploy vritti-ui \
          --image gcr.io/$PROJECT_ID/vritti-ui:$BUILD_ID \
          --region us-central1 \
          --platform managed \
          --allow-unauthenticated
      fi

# Run tests and build on all branches
# Deploy staging on develop branch
# Deploy production on main branch
trigger:
  github:
    owner: ypratap11
    name: vritti
    push:
      branch: '^(main|develop).*

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_8'
```

---

## Environment Configuration

### Production Environment Variables
```bash
# Set production environment variables
gcloud run services update vritti-api \
  --region=us-central1 \
  --set-env-vars="
    ENVIRONMENT=production,
    GCP_PROJECT_ID=vritti-ai-prod,
    GCP_LOCATION=us-central1,
    REDIS_URL=redis://redis-cluster:6379,
    INVOICE_STORAGE_BUCKET=vritti-invoices-prod,
    MAX_FILE_SIZE_MB=25,
    AI_CONFIDENCE_THRESHOLD=0.8,
    QB_ENVIRONMENT=production
  " \
  --set-secrets="
    DATABASE_URL=vritti-database-url:latest,
    JWT_SECRET=vritti-jwt-secret:latest,
    QB_CLIENT_ID=vritti-qb-client-id:latest,
    QB_CLIENT_SECRET=vritti-qb-client-secret:latest
  "
```

### Development Environment Setup
```bash
# Create development environment
gcloud run deploy vritti-api-dev \
  --source=./backend \
  --region=us-central1 \
  --set-env-vars="
    ENVIRONMENT=development,
    GCP_PROJECT_ID=vritti-ai-prod,
    DEBUG=true,
    QB_ENVIRONMENT=sandbox
  " \
  --allow-unauthenticated
```

---

## Monitoring & Alerting Commands

### Health Check Endpoints
```bash
# Test all health endpoints
curl https://api.vritti.ai/health
curl https://api.vritti.ai/health/detailed
curl https://api.vritti.ai/health/database
curl https://api.vritti.ai/health/integrations

# Monitor key metrics
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="vritti-api"' \
  --limit=50 \
  --format="table(timestamp,textPayload)"

# Check current resource usage
gcloud run services describe vritti-api \
  --region=us-central1 \
  --format="export"
```

This comprehensive GCP deployment guide provides everything needed to deploy Vritti as a production-ready, scalable SaaS platform with proper monitoring, security, and disaster recovery capabilities.