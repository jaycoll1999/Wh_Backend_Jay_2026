from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from uuid import UUID

from db.session import get_db
from schemas.device import DeviceResponse as DeviceModelResponse, DeviceCreate, DeviceRegisterRequest, DeviceType, DeviceListResponse
from services.device_service import DeviceService
from models.device import SessionStatus
from services.device_sync_service import device_sync_service
from core.plan_validator import check_busi_user_plan

from core.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Devices"])

def get_device_service(db: Session = Depends(get_db)) -> DeviceService:
    return DeviceService(db)

async def get_current_busi_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload

@router.post("/register", response_model=Dict[str, Any])
async def register_device(
    request: Request,
    token_payload: dict = Depends(get_current_busi_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """Register a new device for the authenticated user"""
    try:
        # ✅ 2. Add Input Validation
        body = {}
        try:
            body = await request.json()
            logger.info(f"📥 Incoming device registration: {body}")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # ✅ 3. Fix User Context Handling
        user_id = token_payload.get("sub")
        if not user_id:
            logger.error("❌ User ID missing in token payload")
            raise HTTPException(status_code=401, detail="Authentication failed: User identity missing")
        
        user_id = str(user_id)

        # Validate mandatory fields
        device_name = body.get("device_name")
        device_type = body.get("device_type")
        
        if not device_name or not str(device_name).strip():
            raise HTTPException(status_code=400, detail="device_name is required and cannot be empty")
        
        if not device_type or not str(device_type).strip():
            # FALLBACK: If instruction says check it's present, we check.
            # But the payload example showed "web", so we enforce it.
            raise HTTPException(status_code=400, detail="device_type is required")

        # ✅ 4. Fix Database Insert Safely
        try:
            from schemas.device import DeviceType, DeviceRegisterRequest
            
            # Safe Enum Conversion
            try:
                final_device_type = DeviceType(str(device_type).lower().strip())
            except ValueError:
                valid_types = [e.value for e in DeviceType]
                raise HTTPException(status_code=400, detail=f"Invalid device_type. Must be one of: {valid_types}")
            
            # Create device register request
            device_request = DeviceRegisterRequest(
                user_id=user_id,
                device_name=str(device_name).strip(),
                device_type=final_device_type
            )
            
            # Register device using the service
            device = device_service.register_device(user_id, device_request)
            
            # ✅ 5. Ensure Response Format
            # We return success: true and the device object.
            # We also include device_id at root for compatibility with legacy frontend callers.
            return {
                "success": True,
                "device_id": str(device.device_id), # Compatibility Layer
                "device": {
                    "device_id": str(device.device_id),
                    "device_name": device.device_name,
                    "device_type": device.device_type.value,
                    "session_status": device.session_status.value,
                    "created_at": device.created_at.isoformat() if device.created_at else None,
                    "is_active": device.is_active
                }
            }

        except ValueError as val_err:
            logger.warning(f"⚠️ Registration logic error: {val_err}")
            raise HTTPException(status_code=400, detail=str(val_err))
        except Exception as db_err:
            # 🔥 ADDED: Better error logging to expose the real error
            logger.error(f"[DEVICE_REGISTER] ❌ Full error: {str(db_err)}")
            raise HTTPException(
                status_code=500, 
                detail="A database error occurred. Please ensure the device name is unique and try again."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔥 Critical error in register_device: {e}")
        # 🔥 ADDED: Better error logging here too
        logger.error(f"[DEVICE_REGISTER_CRITICAL] ❌ Full error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/", response_model=List[DeviceModelResponse])
async def get_devices(
    session_status: Optional[str] = Query(None),
    token_payload: dict = Depends(get_current_busi_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """Get all devices for the authenticated user, optionally filtered by status"""
    try:
        user_id = str(token_payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        devices = device_service.get_user_devices(user_id, session_status)
        return devices
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get devices: {str(e)}")

@router.get("/unofficial/connected")
async def get_connected_unofficial_device(
    token_payload: dict = Depends(get_current_busi_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """Get the first connected unofficial device for the authenticated user"""
    try:
        user_id = str(token_payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 🔥 FORCE SYNC: Ensure we have the latest status from engine before returning connected devices
        # Use fresh session to avoid holding the request's connection open during HTTP calls
        try:
            from services.device_sync_service import device_sync_service
            from db.session import SessionLocal
            with SessionLocal() as sync_db:
                device_sync_service.sync_user_devices(sync_db, user_id)
            logger.info(f"🔄 Synced devices for user {user_id} before returning connected list")
        except Exception as sync_err:
            logger.warning(f"⚠️ Auto-sync failed for user {user_id}: {sync_err}")

        # Search for devices with 'connected' status only
        devices = device_service.get_user_devices(user_id, session_status="connected")
            
        # Filter for unofficial types only (web, mobile, desktop)
        unofficial_types = ["web", "mobile", "desktop"]
        connected_unofficial = [d for d in devices if d.device_type.value in unofficial_types]
        
        if connected_unofficial:
            # Return list format as expected by frontend's response.data.devices
            device_list = []
            for device in connected_unofficial:
                device_list.append({
                    "device_id": str(device.device_id),
                    "device_name": device.device_name,
                    "session_status": device.session_status.value,
                    "device_type": device.device_type.value
                })
            return {
                "success": True,
                "devices": device_list
            }
        else:
            return {
                "success": False,
                "devices": [],
                "message": "No connected unofficial device found"
            }
    except Exception as e:
        logger.error(f"Error getting connected unofficial device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_id}")
async def get_device(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service)
):
    """Get a specific device by ID"""
    try:
        device = device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return device
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device: {str(e)}")

@router.patch("/{device_id}/status")
async def update_device_status(
    device_id: str,
    request: dict,
    device_service: DeviceService = Depends(get_device_service)
):
    """Update device status - called by WhatsApp Engine"""
    try:
        logger.info(f"🔄 Updating device {device_id} status: {request}")
        
        # Extract session_status from request body
        session_status = request.get("session_status", "unknown")
        ip_address = request.get("ip_address")
        
        # Update device status in database
        device = device_service.update_device_status(device_id, session_status, ip_address)
        
        if device:
            logger.info(f"✅ Device {device_id} status updated successfully")
            return {"success": True, "message": "Device status updated"}
        else:
            logger.warning(f"⚠️ Device {device_id} not found - returning 404")
            raise HTTPException(status_code=404, detail="Device not found")
            
    except Exception as e:
        # 🔥 CRITICAL: If the database is unreachable (OperationalError), 
        # we log the warning but return a 200 OK to the engine.
        # This prevents the engine from retrying indefinitely and flooding our logs/connections.
        error_msg = str(e)
        if "OperationalError" in error_msg or "SSL connection" in error_msg or "closed unexpectedly" in error_msg:
            logger.warning(f"⚠️ Database connection failure during status update for {device_id}. Suppressing retry flood.")
            return {"success": False, "message": "Database currently unavailable, update deferred"}
            
        logger.error(f"Error updating device {device_id} status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update device status: {str(e)}")

@router.post("/{device_id}/start")
async def start_device_session(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service)
):
    """Start/initialize a WhatsApp session for a device - proxies to WhatsApp Engine"""
    try:
        # Validate device exists in database first
        device = device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found in database")
        
        # Proxy to WhatsApp Engine
        from services.whatsapp_engine_service import WhatsAppEngineService
        engine_service = WhatsAppEngineService(device_service.db)
        result = engine_service.start_session(device_id)
        
        if result.get("success"):
            return {"status": "ok", "message": "Session start initiated", "data": result.get("result")}
        else:
            raise HTTPException(status_code=502, detail=result.get("error", "Failed to start session"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start device session: {str(e)}")

@router.get("/{device_id}/qr")
async def get_device_qr(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service)
):
    """Get QR code for a device - proxies to WhatsApp Engine"""
    try:
        # Validate device exists in database first
        device = device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found in database")
        
        # Proxy to WhatsApp Engine
        from services.whatsapp_engine_service import WhatsAppEngineService
        engine_service = WhatsAppEngineService(device_service.db)
        result = engine_service.get_qr_code(device_id)
        
        if result.get("success"):
            data = result.get("data", {})
            qr_code = data.get("qr_code") or data.get("qr")
            if qr_code:
                return {"qr_code": qr_code, "status": "qr_ready"}
            elif data.get("status") == "connected":
                return {"qr_code": None, "status": "connected"}
            else:
                return {"qr_code": None, "status": data.get("status", "generating")}
        else:
            error = result.get("error", "QR code not available")
            if "ENGINE_NOT_READY" in str(error):
                raise HTTPException(status_code=502, detail=f"ENGINE_NOT_READY: {error}")
            raise HTTPException(status_code=404, detail=error)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QR for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get QR code: {str(e)}")

@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service)
):
    """Delete/logout a WhatsApp device"""
    try:
        result = device_service.logout_device(device_id)
        
        if result.get("success"):
            return {"message": "Device logged out successfully", "status": result.get("status")}
        else:
            error = result.get("error", "Failed to logout device")
            if error == "device_not_found":
                raise HTTPException(status_code=404, detail="Device not found")
            raise HTTPException(status_code=500, detail=error)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete device: {str(e)}")

@router.get("/official/list", response_model=Dict[str, Any])
async def get_official_devices(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    token_payload: dict = Depends(get_current_busi_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """Get official WhatsApp devices for the authenticated user with pagination"""
    try:
        user_id = str(token_payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        devices = device_service.get_devices_by_user_and_type(
            user_id, 
            DeviceType.OFFICIAL, 
            skip=(page - 1) * size, 
            limit=size
        )
        
        # Verify official config health to dynamically determine connection status
        from services.official_whatsapp_config_service import OfficialWhatsAppConfigService
        from models.device import SessionStatus
        config_service = OfficialWhatsAppConfigService(device_service.db)
        config = config_service.get_config_by_user_id(user_id)
        
        is_healthy = False
        if config and config.is_active and config.access_token:
            try:
                # This performs a real API call to Meta to verify token validity
                profile_result = config_service.get_business_profile(config)
                is_healthy = profile_result.success
            except Exception as ex:
                logger.warning(f"Failed to check official config health for user {user_id}: {ex}")
                is_healthy = False

        # Convert to response format
        device_list = []
        for device in devices:
            current_status = device.session_status
            
            # Dynamically push status change to database if it differs
            if is_healthy and current_status != SessionStatus.connected:
                device.session_status = SessionStatus.connected
                device_service.db.commit()
                current_status = SessionStatus.connected
            elif not is_healthy and current_status != SessionStatus.disconnected:
                device.session_status = SessionStatus.disconnected
                device_service.db.commit()
                current_status = SessionStatus.disconnected
                
            device_list.append({
                "device_id": str(device.device_id),
                "busi_user_id": str(device.busi_user_id),
                "device_name": device.device_name,
                "device_type": device.device_type.value,
                "session_status": current_status.value,
                "qr_last_generated": device.qr_last_generated.isoformat() if device.qr_last_generated else None,
                "ip_address": device.ip_address,
                "last_active": device.last_active.isoformat() if device.last_active else None,
                "created_at": device.created_at.isoformat() if device.created_at else None,
                "updated_at": device.updated_at.isoformat() if device.updated_at else None
            })
        
        return {
            "devices": device_list,
            "total": len(device_list),
            "page": page,
            "size": size
        }
    except Exception as e:
        logger.error(f"Error getting official devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get official devices: {str(e)}")

@router.get("/unofficial/list", response_model=Dict[str, Any])
async def get_unofficial_devices(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sync: bool = Query(True), # 🔥 NEW: Auto-sync from engine by default
    token_payload: dict = Depends(get_current_busi_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """Get unofficial WhatsApp devices for the authenticated user with pagination"""
    try:
        user_id = str(token_payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 🔥 STEP 1: Sync from Engine to pull latest status (pull connected state)
        if sync:
            try:
                logger.info(f"🔄 Auto-syncing devices for user {user_id} before listing...")
                from db.session import SessionLocal
                with SessionLocal() as sync_db:
                    device_sync_service.sync_user_devices(sync_db, user_id)
            except Exception as sync_err:
                logger.warning(f"⚠️ Auto-sync failed for user {user_id}: {sync_err}")
                # Continue anyway, show what we have in DB
        
        # Get all unofficial device types (web, mobile, desktop)
        unofficial_devices = []
        for device_type in [DeviceType.WEB, DeviceType.MOBILE, DeviceType.DESKTOP]:
            devices = device_service.get_devices_by_user_and_type(
                user_id, 
                device_type, 
                skip=(page - 1) * size, 
                limit=size
            )
            unofficial_devices.extend(devices)
        
        # Convert to response format
        device_list = []
        for device in unofficial_devices:
            device_list.append({
                "device_id": str(device.device_id),
                "busi_user_id": str(device.busi_user_id),
                "device_name": device.device_name,
                "device_type": device.device_type.value,
                "session_status": device.session_status.value,
                "qr_last_generated": device.qr_last_generated.isoformat() if device.qr_last_generated else None,
                "ip_address": device.ip_address,
                "last_active": device.last_active.isoformat() if device.last_active else None,
                "created_at": device.created_at.isoformat() if device.created_at else None,
                "updated_at": device.updated_at.isoformat() if device.updated_at else None
            })
        
        return {
            "devices": device_list,
            "total": len(device_list),
            "page": page,
            "size": size
        }
    except Exception as e:
        logger.error(f"Error getting unofficial devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get unofficial devices: {str(e)}")

@router.post("/heal/orphaned")
async def heal_orphaned_devices(
    device_service: DeviceService = Depends(get_device_service)
):
    """
    🔥 REQUIRED BY FRONTEND
    Scan all active devices and mark those not in engine as orphaned
    """
    try:
        logger.info("🛡️ HEAL ORPHANED API: Starting global scan")
        count = device_service.heal_orphaned_devices()
        return {
            "success": True,
            "message": f"Scan complete. {count} orphaned devices detected and updated.",
            "healed_count": count
        }
    except Exception as e:
        logger.error(f"❌ Heal failed: {e}")
        raise HTTPException(status_code=500, detail=f"Heal process failed: {str(e)}")

@router.post("/monitor/start")
async def start_device_monitoring():
    """
    🔥 NEW: Start continuous device monitoring service
    """
    try:
        from services.device_monitor_service import start_device_monitoring
        start_device_monitoring()
        logger.info("🚀 Device monitoring service started via API")
        return {
            "success": True,
            "message": "Device monitoring service started successfully"
        }
    except Exception as e:
        logger.error(f"❌ Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")

@router.post("/monitor/stop")
async def stop_device_monitoring():
    """
    🔥 NEW: Stop continuous device monitoring service
    """
    try:
        from services.device_monitor_service import stop_device_monitoring
        stop_device_monitoring()
        logger.info("🛑 Device monitoring service stopped via API")
        return {
            "success": True,
            "message": "Device monitoring service stopped successfully"
        }
    except Exception as e:
        logger.error(f"❌ Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")

@router.post("/monitor/force-sync")
async def force_sync_all_devices():
    """
    🔥 NEW: Force immediate sync of all devices
    """
    try:
        from services.device_monitor_service import device_monitor_service
        result = device_monitor_service.force_sync_all_devices()
        return result
    except Exception as e:
        logger.error(f"❌ Force sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Force sync failed: {str(e)}")
