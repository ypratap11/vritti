# test_database.py - Test database connection and constraints

import sys
import os

sys.path.append('.')

from src.database.connection import get_db, engine
from src.models.tenant import Invoice, Tenant
from src.services.invoice_service import InvoiceService
from src.utils.currency_parser import clean_invoice_amounts
from sqlalchemy import text


def test_database_connection():
    """Test database connection and constraints"""

    print("🗄️ Testing Database Connection and Constraints")
    print("=" * 60)

    # Test 1: Database connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection: SUCCESS")
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
        return False

    # Test 2: Tables exist
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        required_tables = ['invoices', 'tenants', 'tenant_users']
        for table in required_tables:
            if table in tables:
                print(f"✅ Table '{table}': EXISTS")
            else:
                print(f"❌ Table '{table}': MISSING")

    except Exception as e:
        print(f"❌ Table inspection: FAILED - {e}")

    # Test 3: Invoice constraints
    try:
        db = next(get_db())

        # Test Dublin Nissan data with constraints
        dublin_data = {
            "vendor_name": "Dublin Nissan",
            "total_amount": "$876.99",  # This will be cleaned
            "tax_amount": "$76.99",  # This will be cleaned
            "currency": "USD",
            "notes": "Database constraint test"
        }

        print(f"\n🧪 Testing Dublin Nissan Data Validation")
        print("-" * 40)
        print(f"Original: {dublin_data}")

        # Clean the data
        cleaned = clean_invoice_amounts(dublin_data)
        print(f"Cleaned:  {cleaned}")

        # Validate constraints
        constraints = [
            ("total_amount is float", isinstance(cleaned['total_amount'], (int, float))),
            ("total_amount >= 0", cleaned['total_amount'] >= 0),
            ("tax_amount is float", isinstance(cleaned['tax_amount'], (int, float))),
            ("tax_amount >= 0", cleaned['tax_amount'] >= 0),
            ("currency length = 3", len(cleaned['currency']) == 3),
            ("Dublin amount correct", cleaned['total_amount'] == 876.99)
        ]

        all_passed = True
        for constraint, passed in constraints:
            status = "✅" if passed else "❌"
            print(f"{status} {constraint}")
            if not passed:
                all_passed = False

        print(f"\n🎯 Constraint Validation: {'✅ PASSED' if all_passed else '❌ FAILED'}")

        db.close()
        return all_passed

    except Exception as e:
        print(f"❌ Constraint testing: FAILED - {e}")
        return False


def test_invoice_service():
    """Test invoice service with Dublin Nissan data"""

    print(f"\n🧪 Testing Invoice Service")
    print("-" * 40)

    try:
        db = next(get_db())
        service = InvoiceService(db, "Demo-Admin")

        # This would be the actual test - but let's not insert real data yet
        dublin_data = {
            "vendor_name": "Dublin Nissan TEST",
            "total_amount": "$876.99",
            "tax_amount": "$0.00",
            "currency": "USD",
            "notes": "TEST - Database validation"
        }

        # Just test the data cleaning without saving
        from src.utils.currency_parser import clean_invoice_amounts, parse_currency_to_float

        cleaned = clean_invoice_amounts(dublin_data)
        total_amount = parse_currency_to_float(cleaned.get('total_amount'))
        tax_amount = parse_currency_to_float(cleaned.get('tax_amount', 0))

        print(f"✅ Service data cleaning: SUCCESS")
        print(f"   Total: ${total_amount}")
        print(f"   Tax: ${tax_amount}")
        print(f"   Ready for database: {isinstance(total_amount, (int, float))}")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Invoice service test: FAILED - {e}")
        return False


if __name__ == "__main__":
    db_ok = test_database_connection()
    service_ok = test_invoice_service()

    if db_ok and service_ok:
        print(f"\n🎉 ALL DATABASE TESTS PASSED!")
        print(f"✅ Ready to implement Dublin Nissan fix!")
    else:
        print(f"\n❌ SOME TESTS FAILED")
        print(f"📝 Please fix issues before implementing")