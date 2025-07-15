# src/models/tenant.py
"""
Multi-tenant SQLAlchemy models for Vritti AI
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey, JSON, CheckConstraint, \
    UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import TEXT
from src.database.connection import Base
import uuid
from datetime import datetime


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()


class SchemaVersionMixin:
    """Mixin for schema versioning"""
    schema_version = Column(Integer, default=1, nullable=False)


class SubscriptionPlan(Base, TimestampMixin, SoftDeleteMixin, SchemaVersionMixin):
    """Subscription plans (Free, Pro, Enterprise)"""
    __tablename__ = "subscription_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    price_monthly = Column(Float, CheckConstraint('price_monthly >= 0'), nullable=True)
    price_yearly = Column(Float, CheckConstraint('price_yearly >= 0'), nullable=True)
    document_limit = Column(Integer, CheckConstraint('document_limit > 0'), nullable=True)
    user_limit = Column(Integer, CheckConstraint('user_limit > 0'), nullable=True)
    storage_limit_gb = Column(Integer, CheckConstraint('storage_limit_gb > 0'), nullable=True)
    api_calls_limit = Column(Integer, CheckConstraint('api_calls_limit > 0'), nullable=True)
    features = Column(JSON, default=dict)  # {"feature_name": boolean}
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tenants = relationship("Tenant", back_populates="plan")

    def __repr__(self):
        return f"<SubscriptionPlan(name='{self.name}', slug='{self.slug}')>"


class Tenant(Base, TimestampMixin, SoftDeleteMixin, SchemaVersionMixin):
    """Tenant/Company accounts"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    domain = Column(String(255), nullable=True)
    subdomain = Column(String(100), unique=True, nullable=True)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    data_region = Column(String(50), default="us-east", nullable=False)
    compliance_requirements = Column(JSON, default=list)  # ["GDPR", "SOC2", "HIPAA"]
    settings = Column(JSON, default=dict)  # Tenant-specific settings
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    subscription_status = Column(String(50), default="trial", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "data_region IN ('us-east', 'us-west', 'eu', 'asia')",
            name="check_data_region"
        ),
        CheckConstraint(
            "subscription_status IN ('trial', 'active', 'past_due', 'canceled', 'suspended')",
            name="check_subscription_status"
        ),
    )

    # Relationships
    plan = relationship("SubscriptionPlan", back_populates="tenants")
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("TenantUsage", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("TenantAPIKey", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")
    webhooks = relationship("WebhookEndpoint", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(name='{self.name}', slug='{self.slug}')>"

    @property
    def is_trial_expired(self):
        if not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at


class TenantUser(Base, TimestampMixin, SoftDeleteMixin, SchemaVersionMixin):
    """Users within tenant organizations"""
    __tablename__ = "tenant_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)  # bcrypt hash
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(String(50), default="user", nullable=False)
    permissions = Column(JSON, default=list)  # ["invoice.read", "invoice.approve"]
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'manager', 'user', 'viewer')",
            name="check_user_role"
        ),
        UniqueConstraint('tenant_id', 'email', 'deleted_at', name='unique_tenant_email'),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    uploaded_documents = relationship("Document", back_populates="uploaded_by_user")
    approved_invoices = relationship("Invoice", back_populates="approved_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<TenantUser(email='{self.email}', role='{self.role}')>"

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email

    @property
    def is_locked(self):
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until


class TenantUsage(Base, SchemaVersionMixin):
    """Track tenant usage for billing and limits"""
    __tablename__ = "tenant_usage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    documents_processed = Column(Integer, CheckConstraint('documents_processed >= 0'), default=0)
    api_calls = Column(Integer, CheckConstraint('api_calls >= 0'), default=0)
    storage_used_gb = Column(Float, CheckConstraint('storage_used_gb >= 0'), default=0)
    processing_time_minutes = Column(Integer, CheckConstraint('processing_time_minutes >= 0'), default=0)
    overage_charges = Column(Float, CheckConstraint('overage_charges >= 0'), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'period_start', 'period_end', name='unique_tenant_period'),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="usage_records")

    def __repr__(self):
        return f"<TenantUsage(tenant_id='{self.tenant_id}', period='{self.period_start}')>"


class TenantAPIKey(Base, TimestampMixin, SoftDeleteMixin, SchemaVersionMixin):
    """API keys for tenant programmatic access"""
    __tablename__ = "tenant_api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # "Production API", "Testing"
    key_prefix = Column(String(20), nullable=False)  # "vrt_live_", "vrt_test_"
    key_hash = Column(String(255), nullable=False)  # SHA-256 hash
    permissions = Column(JSON, default=list)  # ["documents.read", "invoices.write"]
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")

    def __repr__(self):
        return f"<TenantAPIKey(name='{self.name}', tenant_id='{self.tenant_id}')>"

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class Document(Base, TimestampMixin, SoftDeleteMixin, SchemaVersionMixin):
    """Uploaded documents for processing"""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(String(36), ForeignKey("tenant_users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=True)
    file_size = Column(Integer, CheckConstraint('file_size > 0'), nullable=True)
    file_hash = Column(String(255), nullable=False)  # SHA-256 for deduplication
    gcs_path = Column(String(500), nullable=True)  # Google Cloud Storage path
    processing_status = Column(String(20), default="pending", nullable=False)
    extracted_data = Column(JSON, default=dict)  # OCR and AI extracted data
    confidence_score = Column(Float, CheckConstraint('confidence_score >= 0 AND confidence_score <= 1'), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('pdf', 'jpg', 'jpeg', 'png', 'tiff')",
            name="check_file_type"
        ),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed', 'canceled')",
            name="check_processing_status"
        ),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    uploaded_by_user = relationship("TenantUser", back_populates="uploaded_documents")
    invoices = relationship("Invoice", back_populates="document")

    def __repr__(self):
        return f"<Document(filename='{self.filename}', status='{self.processing_status}')>"


class Invoice(Base, TimestampMixin, SoftDeleteMixin, SchemaVersionMixin):
    """Processed invoice data with approval workflow"""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    vendor_name = Column(String(255), nullable=True)
    vendor_address = Column(Text, nullable=True)
    vendor_tax_id = Column(String(50), nullable=True)
    invoice_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    total_amount = Column(Float, CheckConstraint('total_amount >= 0'), nullable=True)
    tax_amount = Column(Float, CheckConstraint('tax_amount >= 0'), default=0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    line_items = Column(JSON, default=list)  # Detailed line items
    approval_status = Column(String(20), default="pending", nullable=False)
    approval_workflow = Column(JSON, default=dict)  # Multi-step approval tracking
    approved_by = Column(String(36), ForeignKey("tenant_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    payment_status = Column(String(20), default="unpaid", nullable=False)
    payment_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # ["urgent", "recurring", "office_supplies"]

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'on_hold')",
            name="check_approval_status"
        ),
        CheckConstraint(
            "payment_status IN ('unpaid', 'paid', 'partial', 'overdue')",
            name="check_payment_status"
        ),
        CheckConstraint("length(currency) = 3", name="check_currency_length"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="invoices")
    document = relationship("Document", back_populates="invoices")
    approved_by_user = relationship("TenantUser", back_populates="approved_invoices")

    def __repr__(self):
        return f"<Invoice(number='{self.invoice_number}', vendor='{self.vendor_name}', status='{self.approval_status}')>"


class AuditLog(Base):
    """Audit trail for compliance and security"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("tenant_users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # "invoice.approved", "user.created"
    resource_type = Column(String(50), nullable=False)  # "invoice", "user", "document"
    resource_id = Column(String(36), nullable=False)
    old_values = Column(JSON, nullable=True)  # Before state
    new_values = Column(JSON, nullable=True)  # After state
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("TenantUser", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', resource='{self.resource_type}:{self.resource_id}')>"


class WebhookEndpoint(Base, TimestampMixin, SoftDeleteMixin, SchemaVersionMixin):
    """Webhook endpoints for integrations"""
    __tablename__ = "webhook_endpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False)  # ["invoice.approved", "document.processed"]
    secret_hash = Column(String(255), nullable=False)  # HMAC secret for verification
    is_active = Column(Boolean, default=True, nullable=False)
    last_success = Column(DateTime(timezone=True), nullable=True)
    last_failure = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, default=0, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="webhooks")

    def __repr__(self):
        return f"<WebhookEndpoint(url='{self.url}', tenant_id='{self.tenant_id}')>"