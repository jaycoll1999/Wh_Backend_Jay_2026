import sys
import os
sys.path.append(os.getcwd())
from db.session import SessionLocal
from models.busi_user import BusiUser
from models.device import Device, SessionStatus

db = SessionLocal()
users = db.query(BusiUser).all()
for u in users:
    devices = db.query(Device).filter(Device.busi_user_id == str(u.busi_user_id)).all()
    print(f"User: {u.business_name}, ID: {u.busi_user_id}, Devices: {len(devices)}")
    for d in devices:
        print(f"  Device: {d.session_status}, Active: {d.is_active}")
        
    is_connected = db.query(Device).filter(
        Device.busi_user_id == str(u.busi_user_id),
        Device.session_status == SessionStatus.connected,
        Device.is_active == True
    ).first() is not None
    print(f"  map_busi_user_to_response is_connected: {is_connected}")
