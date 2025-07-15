# scripts/create_multitenant_schema_enhanced.py
"""
Enhanced SQLite Multi-Tenant Schema Migration
Production-ready schema with security, scalability, and compliance features
"""

import sqlite3
import uuid
import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta
import json


def create_enhanced_multitenant_schema():
    """Create production-ready multi-tenant tables in SQLite with all enhancements"""

    conn = sqlite3.connect('./vritti_dev.db')
    cursor = conn.cursor()

    print("🚀 Creating enhanced multi-tenant schema...")

    # Enable foreign key constraints (Critical for SQLite)
    cursor.execute("PRAGMA foreign_keys = ON")

    # Enable Write-Ahead Logging for better performance
    cursor.execute("PRAGMA journal_mode = WAL")

    # 1. Create subscription_plans table with enhancements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            price_monthly REAL CHECK (price_monthly >= 0),
            price_yearly REAL CHECK (price_yearly >= 0),
            document_limit INTEGER CHECK (document_limit > 0),
            user_limit INTEGER CHECK (user_limit > 0),
            storage_limit_gb INTEGER CHECK (storage_limit_gb > 0),
            api_calls_limit INTEGER CHECK (api_calls_limit > 0),
            features TEXT DEFAULT '{}', -- JSON: {"feature_name": boolean}
            is_active BOOLEAN DEFAULT 1,
            schema_version INTEGER DEFAULT 1, -- For future migrations
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL -- Soft delete support
        )
    ''')

    # 2. Create tenants table with enhanced security
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            domain TEXT,
            subdomain TEXT UNIQUE,
            plan_id TEXT NOT NULL REFERENCES subscription_plans(id),
            stripe_customer_id TEXT UNIQUE, -- Ensure one Stripe customer per tenant
            data_region TEXT DEFAULT 'us-east' CHECK (data_region IN ('us-east', 'us-west', 'eu', 'asia')),
            compliance_requirements TEXT DEFAULT '[]', -- JSON array: ["GDPR", "SOC2", "HIPAA"]
            settings TEXT DEFAULT '{}', -- JSON: tenant-specific settings
            onboarding_completed BOOLEAN DEFAULT 0,
            trial_ends_at TIMESTAMP,
            subscription_status TEXT DEFAULT 'trial' CHECK (subscription_status IN ('trial', 'active', 'past_due', 'canceled', 'suspended')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL, -- Soft delete support
            is_active BOOLEAN DEFAULT 1,
            schema_version INTEGER DEFAULT 1
        )
    ''')

    # 3. Create tenant_users table with security enhancements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenant_users (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            password_hash TEXT, -- bcrypt hash, never plain text
            first_name TEXT,
            last_name TEXT,
            role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'user', 'viewer')),
            permissions TEXT DEFAULT '[]', -- JSON array: ["invoice.read", "invoice.approve"]
            is_active BOOLEAN DEFAULT 1,
            email_verified BOOLEAN DEFAULT 0,
            last_login TIMESTAMP,
            login_attempts INTEGER DEFAULT 0, -- Security: track failed logins
            locked_until TIMESTAMP NULL, -- Security: account lockout
            password_reset_token TEXT NULL, -- Security: password reset
            password_reset_expires TIMESTAMP NULL,
            email_verification_token TEXT NULL,
            email_verification_expires TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL, -- Soft delete support
            schema_version INTEGER DEFAULT 1,
            UNIQUE(tenant_id, email, deleted_at) -- Allow same email if soft deleted
        )
    ''')

    # 4. Create tenant_usage table with enhanced tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenant_usage (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            documents_processed INTEGER DEFAULT 0 CHECK (documents_processed >= 0),
            api_calls INTEGER DEFAULT 0 CHECK (api_calls >= 0),
            storage_used_gb REAL DEFAULT 0 CHECK (storage_used_gb >= 0),
            processing_time_minutes INTEGER DEFAULT 0 CHECK (processing_time_minutes >= 0),
            overage_charges REAL DEFAULT 0 CHECK (overage_charges >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            schema_version INTEGER DEFAULT 1,
            UNIQUE(tenant_id, period_start, period_end) -- One record per period
        )
    ''')

    # 5. Create tenant_api_keys table with enhanced security
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenant_api_keys (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name TEXT NOT NULL, -- Human-readable name: "Production API", "Testing"
            key_prefix TEXT NOT NULL, -- Public part: "vrt_live_" or "vrt_test_"
            key_hash TEXT NOT NULL, -- SHA-256 hash of full key, never store plain text
            permissions TEXT DEFAULT '[]', -- JSON: ["documents.read", "invoices.write"]
            last_used TIMESTAMP,
            usage_count INTEGER DEFAULT 0, -- Track API key usage
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL, -- Soft delete support
            schema_version INTEGER DEFAULT 1
        )
    ''')

    # 6. Create documents table with enhanced metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            uploaded_by TEXT NOT NULL REFERENCES tenant_users(id), -- Track who uploaded
            filename TEXT NOT NULL, -- Sanitized filename
            original_filename TEXT NOT NULL, -- Original user filename
            file_type TEXT CHECK (file_type IN ('pdf', 'jpg', 'jpeg', 'png', 'tiff')),
            file_size INTEGER CHECK (file_size > 0), -- Bytes
            file_hash TEXT NOT NULL, -- SHA-256 for duplicate detection
            gcs_path TEXT, -- Google Cloud Storage path
            processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'canceled')),
            extracted_data TEXT DEFAULT '{}', -- JSON: OCR and AI extracted data
            confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
            processing_time_ms INTEGER, -- Performance tracking
            error_message TEXT, -- Store error details if processing fails
            retry_count INTEGER DEFAULT 0, -- Track processing retries
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL, -- Soft delete support
            schema_version INTEGER DEFAULT 1
        )
    ''')

    # 7. Create invoices table with enhanced workflow
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            document_id TEXT REFERENCES documents(id), -- Link to source document
            invoice_number TEXT,
            vendor_name TEXT,
            vendor_address TEXT,
            vendor_tax_id TEXT, -- For compliance
            invoice_date DATE,
            due_date DATE,
            total_amount REAL CHECK (total_amount >= 0),
            tax_amount REAL DEFAULT 0 CHECK (tax_amount >= 0),
            currency TEXT DEFAULT 'USD' CHECK (length(currency) = 3), -- ISO currency codes
            line_items TEXT DEFAULT '[]', -- JSON: detailed line items
            approval_status TEXT DEFAULT 'pending' CHECK (approval_status IN ('pending', 'approved', 'rejected', 'on_hold')),
            approval_workflow TEXT DEFAULT '{}', -- JSON: multi-step approval tracking
            approved_by TEXT REFERENCES tenant_users(id), -- Who approved
            approved_at TIMESTAMP,
            rejection_reason TEXT, -- Why rejected
            payment_status TEXT DEFAULT 'unpaid' CHECK (payment_status IN ('unpaid', 'paid', 'partial', 'overdue')),
            payment_date DATE,
            notes TEXT, -- Internal notes
            tags TEXT DEFAULT '[]', -- JSON: ["urgent", "recurring", "office_supplies"]
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL, -- Soft delete support
            schema_version INTEGER DEFAULT 1
        )
    ''')

    # 8. Create audit_logs table for compliance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id TEXT REFERENCES tenant_users(id), -- Who performed the action
            action TEXT NOT NULL, -- "invoice.approved", "user.created", "document.uploaded"
            resource_type TEXT NOT NULL, -- "invoice", "user", "document"
            resource_id TEXT NOT NULL, -- ID of the affected resource
            old_values TEXT, -- JSON: before state
            new_values TEXT, -- JSON: after state
            ip_address TEXT, -- For security tracking
            user_agent TEXT, -- Browser/API client info
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 9. Create webhook_endpoints table for integrations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhook_endpoints (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            events TEXT NOT NULL, -- JSON: ["invoice.approved", "document.processed"]
            secret_hash TEXT NOT NULL, -- HMAC secret for verification
            is_active BOOLEAN DEFAULT 1,
            last_success TIMESTAMP,
            last_failure TIMESTAMP,
            failure_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL,
            schema_version INTEGER DEFAULT 1
        )
    ''')

    # 10. Create comprehensive indexes for performance
    indexes = [
        # Tenants
        "CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_tenants_subdomain ON tenants(subdomain) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_tenants_stripe ON tenants(stripe_customer_id) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(is_active, deleted_at)",

        # Users
        "CREATE INDEX IF NOT EXISTS idx_tenant_users_email ON tenant_users(email) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_tenant_users_tenant ON tenant_users(tenant_id) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_tenant_users_active ON tenant_users(tenant_id, is_active) WHERE deleted_at IS NULL",

        # Documents
        "CREATE INDEX IF NOT EXISTS idx_documents_tenant ON documents(tenant_id) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at) WHERE deleted_at IS NULL",

        # Invoices
        "CREATE INDEX IF NOT EXISTS idx_invoices_tenant ON invoices(tenant_id) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_invoices_approval ON invoices(approval_status) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_invoices_vendor ON invoices(vendor_name) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_invoices_amount ON invoices(total_amount) WHERE deleted_at IS NULL",

        # Usage tracking
        "CREATE INDEX IF NOT EXISTS idx_usage_tenant_period ON tenant_usage(tenant_id, period_start)",

        # API Keys
        "CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON tenant_api_keys(tenant_id) WHERE deleted_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON tenant_api_keys(key_hash) WHERE deleted_at IS NULL",

        # Audit logs
        "CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_logs(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)",
        "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)",

        # Webhooks
        "CREATE INDEX IF NOT EXISTS idx_webhooks_tenant ON webhook_endpoints(tenant_id) WHERE deleted_at IS NULL"
    ]

    for index in indexes:
        cursor.execute(index)

    # 11. Create triggers for auto-updating timestamps
    triggers = [
        '''
        CREATE TRIGGER IF NOT EXISTS update_subscription_plans_timestamp 
        AFTER UPDATE ON subscription_plans
        BEGIN
            UPDATE subscription_plans SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        ''',
        '''
        CREATE TRIGGER IF NOT EXISTS update_tenants_timestamp 
        AFTER UPDATE ON tenants
        BEGIN
            UPDATE tenants SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        ''',
        '''
        CREATE TRIGGER IF NOT EXISTS update_tenant_users_timestamp 
        AFTER UPDATE ON tenant_users
        BEGIN
            UPDATE tenant_users SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        ''',
        '''
        CREATE TRIGGER IF NOT EXISTS update_documents_timestamp 
        AFTER UPDATE ON documents
        BEGIN
            UPDATE documents SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        ''',
        '''
        CREATE TRIGGER IF NOT EXISTS update_invoices_timestamp 
        AFTER UPDATE ON invoices
        BEGIN
            UPDATE invoices SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        '''
    ]

    for trigger in triggers:
        cursor.execute(trigger)

    print("✅ Enhanced multi-tenant tables and triggers created!")

    # 12. Insert enhanced subscription plans
    plans = [
        {
            'id': str(uuid.uuid4()),
            'name': 'Free',
            'slug': 'free',
            'description': 'Perfect for trying out Vritti AI',
            'price_monthly': 0.00,
            'price_yearly': 0.00,
            'document_limit': 50,
            'user_limit': 1,
            'storage_limit_gb': 1,
            'api_calls_limit': 1000,
            'features': json.dumps({
                "basic_ocr": True,
                "email_support": True,
                "data_retention_days": 30,
                "webhook_endpoints": 1,
                "api_access": False,
                "custom_fields": False,
                "approval_workflows": False
            })
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Professional',
            'slug': 'pro',
            'description': 'Ideal for small to medium businesses',
            'price_monthly': 49.00,
            'price_yearly': 490.00,
            'document_limit': 1000,
            'user_limit': 5,
            'storage_limit_gb': 10,
            'api_calls_limit': 10000,
            'features': json.dumps({
                "advanced_ocr": True,
                "api_access": True,
                "webhooks": True,
                "priority_support": True,
                "data_retention_days": 365,
                "webhook_endpoints": 5,
                "custom_fields": True,
                "approval_workflows": True,
                "bulk_processing": True
            })
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Enterprise',
            'slug': 'enterprise',
            'description': 'For large organizations with custom needs',
            'price_monthly': 199.00,
            'price_yearly': 1990.00,
            'document_limit': 10000,
            'user_limit': 100,
            'storage_limit_gb': 100,
            'api_calls_limit': 100000,
            'features': json.dumps({
                "unlimited_processing": True,
                "custom_models": True,
                "sso": True,
                "dedicated_support": True,
                "unlimited_retention": True,
                "on_premise": True,
                "webhook_endpoints": -1,
                "advanced_analytics": True,
                "white_label": True,
                "audit_logs": True
            })
        }
    ]

    for plan in plans:
        cursor.execute('''
            INSERT OR IGNORE INTO subscription_plans 
            (id, name, slug, description, price_monthly, price_yearly, 
             document_limit, user_limit, storage_limit_gb, api_calls_limit, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plan['id'], plan['name'], plan['slug'], plan['description'],
            plan['price_monthly'], plan['price_yearly'], plan['document_limit'],
            plan['user_limit'], plan['storage_limit_gb'], plan['api_calls_limit'],
            plan['features']
        ))

    print("✅ Enhanced subscription plans inserted!")

    # 13. Create demo tenant with proper security
    demo_tenant_id = str(uuid.uuid4())
    demo_user_id = str(uuid.uuid4())
    free_plan_id = cursor.execute("SELECT id FROM subscription_plans WHERE slug = 'free'").fetchone()[0]

    # Insert demo tenant
    cursor.execute('''
        INSERT OR IGNORE INTO tenants 
        (id, name, slug, subdomain, plan_id, trial_ends_at, settings, compliance_requirements)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        demo_tenant_id,
        'Demo Company',
        'demo-company',
        'demo',
        free_plan_id,
        datetime.now() + timedelta(days=14),
        json.dumps({
            "demo_account": True,
            "auto_approve_limit": 100,
            "currency": "USD",
            "timezone": "America/New_York"
        }),
        json.dumps(["SOC2"])
    ))

    # Insert demo admin user with proper password hashing
    demo_password = "DemoPassword123!"
    password_hash = bcrypt.hashpw(demo_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cursor.execute('''
        INSERT OR IGNORE INTO tenant_users 
        (id, tenant_id, email, password_hash, first_name, last_name, role, email_verified, permissions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        demo_user_id,
        demo_tenant_id,
        'admin@demo.vritti.ai',
        password_hash,
        'Demo',
        'Admin',
        'admin',
        1,
        json.dumps(["*"])  # Full permissions
    ))

    # Create demo API key with proper hashing
    api_key_id = str(uuid.uuid4())
    api_key = f"vrt_test_{secrets.token_urlsafe(32)}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    cursor.execute('''
        INSERT OR IGNORE INTO tenant_api_keys
        (id, tenant_id, name, key_prefix, key_hash, permissions, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        api_key_id,
        demo_tenant_id,
        'Demo API Key',
        'vrt_test_',
        api_key_hash,
        json.dumps(["documents.read", "documents.write", "invoices.read"]),
        datetime.now() + timedelta(days=365)
    ))

    print("✅ Demo tenant with secure credentials created!")
    print(f"   📧 Email: admin@demo.vritti.ai")
    print(f"   🔑 Password: {demo_password}")
    print(f"   🗝️  API Key: {api_key}")

    # 14. Add initial audit log
    cursor.execute('''
        INSERT INTO audit_logs
        (id, tenant_id, user_id, action, resource_type, resource_id, new_values, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(uuid.uuid4()),
        demo_tenant_id,
        demo_user_id,
        'tenant.created',
        'tenant',
        demo_tenant_id,
        json.dumps({"name": "Demo Company", "plan": "free"}),
        '127.0.0.1'
    ))

    conn.commit()
    conn.close()

    print("\n🎉 Enhanced multi-tenant schema setup complete!")
    print("\n🔒 Security Features Enabled:")
    print("  ✅ Foreign key enforcement")
    print("  ✅ Password hashing (bcrypt)")
    print("  ✅ API key hashing (SHA-256)")
    print("  ✅ Soft deletes")
    print("  ✅ Audit logging")
    print("  ✅ CHECK constraints")
    print("  ✅ Auto-update timestamps")
    print("\n📊 Performance Features:")
    print("  ✅ Comprehensive indexing")
    print("  ✅ WAL mode enabled")
    print("  ✅ Query optimization")
    print("\n🏢 Enterprise Features:")
    print("  ✅ Multi-step approval workflows")
    print("  ✅ Webhook support")
    print("  ✅ Usage tracking")
    print("  ✅ Compliance tracking")

    return True


def verify_enhanced_schema():
    """Verify the enhanced schema was created correctly"""
    conn = sqlite3.connect('./vritti_dev.db')
    cursor = conn.cursor()

    # Check foreign key enforcement
    cursor.execute("PRAGMA foreign_keys")
    fk_status = cursor.fetchone()[0]
    print(f"\n🔗 Foreign Keys: {'✅ Enabled' if fk_status else '❌ Disabled'}")

    # Check WAL mode
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0]
    print(f"📝 Journal Mode: {journal_mode}")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    print("\n📊 Database tables:")
    for table in tables:
        table_name = table[0]
        if table_name.startswith('sqlite_'):
            continue
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count} records")

    # Check triggers
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    triggers = cursor.fetchall()
    print(f"\n⚡ Triggers: {len(triggers)} auto-update triggers")

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
    indexes = cursor.fetchall()
    print(f"🚀 Indexes: {len(indexes)} performance indexes")

    conn.close()


if __name__ == "__main__":
    print("🏗️  Setting up Enhanced Vritti AI Multi-Tenant Database")
    print("=" * 60)

    # Install required packages if not present
    try:
        import bcrypt
    except ImportError:
        print("Installing bcrypt for password hashing...")
        import subprocess

        subprocess.check_call(["pip", "install", "bcrypt"])
        import bcrypt

    create_enhanced_multitenant_schema()
    verify_enhanced_schema()

    print("\n✨ Production-ready multi-tenant platform is ready!")
    print("🔐 Security-first design with compliance features")
    print("📈 Scalable architecture with performance optimizations")
    print("🚀 Ready for your first tenant registration!")