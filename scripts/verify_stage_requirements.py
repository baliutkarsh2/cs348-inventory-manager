"""
Automated verification for Stage 2 requirements (a) and (b):
 - (a) Insert, update, delete on Products using SQLAlchemy ORM
 - (b) Filtered report stats before and after a data change

Run:
  python scripts/verify_stage_requirements.py

This script operates directly on the local SQLite DB at instance/app.db.
"""

from datetime import date
from decimal import Decimal
import os
import sys

# Ensure project root is on sys.path so `import app` works when run as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app, db, seed_if_empty, Category, Supplier, Location, Product


def print_report_stats(category_name: str, min_price: float, max_price: float):
    with app.app_context():
        q = db.session.query(Product)
        cat = Category.query.filter_by(name=category_name).first()
        if cat:
            q = q.filter(Product.category_id == cat.id)
        if min_price is not None:
            q = q.filter(Product.price >= min_price)
        if max_price is not None:
            q = q.filter(Product.price <= max_price)
        results = q.order_by(Product.name.asc()).all()
        if results:
            avg_price = float(sum(float(p.price) for p in results) / len(results))
            avg_stock = sum(p.units_in_stock for p in results) / len(results)
            total_value = float(sum(float(p.price) * p.units_in_stock for p in results))
        else:
            avg_price = avg_stock = total_value = 0.0

        print(f"Report (Category={category_name}, Price=[{min_price}, {max_price}]):")
        print(f"  count={len(results)} avg_price={avg_price:.2f} avg_stock={avg_stock:.2f} total_value={total_value:.2f}")


def main():
    with app.app_context():
        db.create_all()
        seed_if_empty()

        # Choose references
        cat = Category.query.order_by(Category.id).first()
        sup = Supplier.query.order_by(Supplier.id).first()
        loc = Location.query.order_by(Location.id).first()
        assert cat and sup and loc, "Reference tables must be seeded."

        # (b) Report BEFORE change
        print("Before change:")
        print_report_stats(category_name=cat.name, min_price=0, max_price=1000)

        # (a) INSERT a product
        p = Product(
            name="Demo Widget",
            sku="DEMO-W-001",
            price=Decimal("12.34"),
            units_in_stock=10,
            reorder_level=2,
            created_at=date.today(),
            category_id=cat.id,
            supplier_id=sup.id,
            location_id=loc.id,
        )
        db.session.add(p)
        db.session.commit()
        print(f"Inserted product id={p.id}, sku={p.sku}")

        # UPDATE the product
        p.price = Decimal("15.00")
        p.units_in_stock = 25
        db.session.commit()
        print(f"Updated product id={p.id}: price=15.00, units_in_stock=25")

        # (b) Report AFTER change
        print("After change:")
        print_report_stats(category_name=cat.name, min_price=0, max_price=1000)

        # DELETE the product
        db.session.delete(p)
        db.session.commit()
        print(f"Deleted product id={p.id}")


if __name__ == "__main__":
    main()
