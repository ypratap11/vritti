# src/services/invoice_service.py
"""
Multi-tenant invoice service functions
Enhanced versions of your original invoice functions with tenant isolation
"""

from sqlalchemy.orm import Session
from src.models.tenant import Invoice, Document, Tenant, TenantUser, AuditLog
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json


class InvoiceService:
    """Multi-tenant invoice service with enhanced functionality"""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self._validate_tenant()

    def _validate_tenant(self):
        """Ensure tenant exists and is active"""
        tenant = self.db.query(Tenant).filter(
            Tenant.id == self.tenant_id,
            Tenant.is_active == True,
            Tenant.deleted_at.is_(None)
        ).first()

        if not tenant:
            raise ValueError(f"Invalid or inactive tenant: {self.tenant_id}")

        self.tenant = tenant

    def save_invoice_to_db(
            self,
            invoice_data: Dict[str, Any],
            document_id: Optional[str] = None,
            user_id: Optional[str] = None
    ) -> Invoice:
        """
        Save processed invoice to database with tenant isolation
        Enhanced version of the original save_invoice_to_db function
        """

        # Create invoice with tenant context
        db_invoice = Invoice(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            document_id=document_id,
            invoice_number=invoice_data.get('invoice_number'),
            vendor_name=invoice_data.get('vendor_name'),
            vendor_address=invoice_data.get('vendor_address'),
            vendor_tax_id=invoice_data.get('vendor_tax_id'),
            invoice_date=invoice_data.get('invoice_date'),
            due_date=invoice_data.get('due_date'),
            total_amount=invoice_data.get('total_amount'),
            tax_amount=invoice_data.get('tax_amount', 0),
            currency=invoice_data.get('currency', 'USD'),
            line_items=invoice_data.get('line_items', []),
            approval_status='pending',
            payment_status='unpaid',
            notes=invoice_data.get('notes'),
            tags=invoice_data.get('tags', [])
        )

        self.db.add(db_invoice)
        self.db.commit()
        self.db.refresh(db_invoice)

        # Create audit log
        self._create_audit_log(
            action="invoice.created",
            resource_type="invoice",
            resource_id=db_invoice.id,
            new_values={
                "vendor_name": db_invoice.vendor_name,
                "total_amount": db_invoice.total_amount,
                "invoice_number": db_invoice.invoice_number
            },
            user_id=user_id
        )

        return db_invoice

    def search_invoices_by_vendor(self, vendor: str, limit: int = 50) -> List[Invoice]:
        """
        Search invoices by vendor name with tenant isolation
        Enhanced version with better filtering and pagination
        """
        return self.db.query(Invoice).filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.vendor_name.ilike(f"%{vendor}%"),
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.created_at.desc()).limit(limit).all()

    def get_recent_invoices(self, limit: int = 20) -> List[Invoice]:
        """
        Get recent invoices for tenant
        Enhanced with better performance and filtering
        """
        return self.db.query(Invoice).filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.created_at.desc()).limit(limit).all()

    def get_invoices_by_amount_range(
            self,
            min_amount: float,
            max_amount: float,
            limit: int = 100
    ) -> List[Invoice]:
        """
        Get invoices in amount range with tenant isolation
        Enhanced with better performance
        """
        return self.db.query(Invoice).filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.total_amount >= min_amount,
            Invoice.total_amount <= max_amount,
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.total_amount.desc()).limit(limit).all()

    def get_invoices_by_status(self, status: str, limit: int = 50) -> List[Invoice]:
        """Get invoices by approval status"""
        return self.db.query(Invoice).filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.approval_status == status,
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.created_at.desc()).limit(limit).all()

    def get_pending_approvals(self, limit: int = 50) -> List[Invoice]:
        """Get invoices pending approval"""
        return self.get_invoices_by_status('pending', limit)

    def approve_invoice(
            self,
            invoice_id: str,
            user_id: str,
            notes: Optional[str] = None
    ) -> Invoice:
        """
        Approve an invoice with audit trail
        """
        invoice = self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.tenant_id == self.tenant_id,
            Invoice.deleted_at.is_(None)
        ).first()

        if not invoice:
            raise ValueError("Invoice not found")

        if invoice.approval_status != 'pending':
            raise ValueError(f"Invoice already {invoice.approval_status}")

        old_status = invoice.approval_status

        # Update invoice
        invoice.approval_status = 'approved'
        invoice.approved_by = user_id
        invoice.approved_at = datetime.utcnow()
        if notes:
            invoice.notes = notes

        self.db.commit()
        self.db.refresh(invoice)

        # Create audit log
        self._create_audit_log(
            action="invoice.approved",
            resource_type="invoice",
            resource_id=invoice.id,
            old_values={"approval_status": old_status},
            new_values={
                "approval_status": "approved",
                "approved_by": user_id,
                "approved_at": invoice.approved_at.isoformat()
            },
            user_id=user_id
        )

        return invoice

    def reject_invoice(
            self,
            invoice_id: str,
            user_id: str,
            reason: str
    ) -> Invoice:
        """
        Reject an invoice with reason
        """
        invoice = self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.tenant_id == self.tenant_id,
            Invoice.deleted_at.is_(None)
        ).first()

        if not invoice:
            raise ValueError("Invoice not found")

        old_status = invoice.approval_status

        # Update invoice
        invoice.approval_status = 'rejected'
        invoice.rejection_reason = reason

        self.db.commit()
        self.db.refresh(invoice)

        # Create audit log
        self._create_audit_log(
            action="invoice.rejected",
            resource_type="invoice",
            resource_id=invoice.id,
            old_values={"approval_status": old_status},
            new_values={
                "approval_status": "rejected",
                "rejection_reason": reason
            },
            user_id=user_id
        )

        return invoice

    def get_invoice_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get invoice analytics for tenant
        """
        since_date = datetime.utcnow() - timedelta(days=days)

        # Total invoices
        total_invoices = self.db.query(Invoice).filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.created_at >= since_date,
            Invoice.deleted_at.is_(None)
        ).count()

        # Status breakdown
        status_query = self.db.query(
            Invoice.approval_status,
            self.db.func.count(Invoice.id).label('count'),
            self.db.func.sum(Invoice.total_amount).label('total_amount')
        ).filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.created_at >= since_date,
            Invoice.deleted_at.is_(None)
        ).group_by(Invoice.approval_status).all()

        status_breakdown = {
            status: {"count": count, "total_amount": float(total_amount or 0)}
            for status, count, total_amount in status_query
        }

        # Top vendors
        vendor_query = self.db.query(
            Invoice.vendor_name,
            self.db.func.count(Invoice.id).label('count'),
            self.db.func.sum(Invoice.total_amount).label('total_amount')
        ).filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.created_at >= since_date,
            Invoice.deleted_at.is_(None),
            Invoice.vendor_name.isnot(None)
        ).group_by(Invoice.vendor_name).order_by(
            self.db.func.sum(Invoice.total_amount).desc()
        ).limit(10).all()

        top_vendors = [
            {
                "vendor_name": vendor,
                "count": count,
                "total_amount": float(total_amount or 0)
            }
            for vendor, count, total_amount in vendor_query
        ]

        return {
            "period_days": days,
            "total_invoices": total_invoices,
            "status_breakdown": status_breakdown,
            "top_vendors": top_vendors,
            "generated_at": datetime.utcnow().isoformat()
        }

    def _create_audit_log(
            self,
            action: str,
            resource_type: str,
            resource_id: str,
            old_values: Optional[Dict] = None,
            new_values: Optional[Dict] = None,
            user_id: Optional[str] = None
    ):
        """Create audit log entry"""
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address='127.0.0.1'  # You can pass this from the request
        )

        self.db.add(audit_log)
        # Note: Don't commit here, let the calling function handle it


# Convenience functions for backward compatibility
def get_invoice_service(db: Session, tenant_id: str) -> InvoiceService:
    """Get invoice service for a specific tenant"""
    return InvoiceService(db, tenant_id)


# Example usage functions
def save_invoice_to_db(invoice_data: dict, db: Session, tenant_id: str, user_id: str = None):
    """Backward compatible function"""
    service = InvoiceService(db, tenant_id)
    return service.save_invoice_to_db(invoice_data, user_id=user_id)


def search_invoices_by_vendor(vendor: str, db: Session, tenant_id: str):
    """Backward compatible function"""
    service = InvoiceService(db, tenant_id)
    return service.search_invoices_by_vendor(vendor)


def get_recent_invoices(limit: int, db: Session, tenant_id: str):
    """Backward compatible function"""
    service = InvoiceService(db, tenant_id)
    return service.get_recent_invoices(limit)


def get_invoices_by_amount_range(min_amount: float, max_amount: float, db: Session, tenant_id: str):
    """Backward compatible function"""
    service = InvoiceService(db, tenant_id)
    return service.get_invoices_by_amount_range(min_amount, max_amount)