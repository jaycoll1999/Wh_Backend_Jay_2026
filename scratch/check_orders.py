import sys, os
sys.path.append(os.getcwd())
from db.session import SessionLocal
from models.payment_order import PaymentOrder
db = SessionLocal()
orders = db.query(PaymentOrder).limit(10).all()
for o in orders:
    print(f"ID: {o.id}, Plan: {o.plan_name}, Amount: {o.amount}, Credits: {o.credits}")
