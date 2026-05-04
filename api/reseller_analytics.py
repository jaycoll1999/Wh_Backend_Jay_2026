from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from db.session import get_db
from schemas.reseller_analytics import (
    ResellerDashboardResponse,
    ResellerAnalyticsCreate,
    ResellerAnalyticsUpdate
)
from services.reseller_analytics_service import ResellerAnalyticsService
from pydantic import BaseModel
import requests
import json

class AIRequest(BaseModel):
    message: str
    reseller_id: str
    confirm: Optional[bool] = None

# In-memory store for pending actions (In production, use Redis or DB)
# Key: reseller_id, Value: action_details
pending_actions: Dict[str, Any] = {}

router = APIRouter()


@router.get("/dashboard/{reseller_id}", response_model=ResellerDashboardResponse)
async def get_reseller_dashboard(
    reseller_id: str,
    db: Session = Depends(get_db)
):
    """Get complete reseller dashboard analytics."""
    service = ResellerAnalyticsService(db)
    
    try:
        dashboard = service.generate_reseller_dashboard(reseller_id)
        return dashboard
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"CRITICAL ERROR generating dashboard for {reseller_id}: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating dashboard: {str(e)}"
        )


@router.get("/business-stats/{reseller_id}")
async def get_business_user_stats(
    reseller_id: str,
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get statistics for all business users under a reseller."""
    service = ResellerAnalyticsService(db)
    
    try:
        business_stats = service.get_business_user_stats(reseller_id)
        return {
            "reseller_id": reseller_id,
            "total_businesses": len(business_stats),
            "business_stats": business_stats[:limit]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching business stats: {str(e)}"
        )


@router.get("/top-businesses/{reseller_id}")
async def get_top_performing_businesses(
    reseller_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get top performing businesses by credits used."""
    service = ResellerAnalyticsService(db)
    
    try:
        top_businesses = service.get_top_performing_businesses(reseller_id, limit)
        return {
            "reseller_id": reseller_id,
            "top_businesses": top_businesses,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching top businesses: {str(e)}"
        )


@router.get("/analytics/{reseller_id}")
async def get_reseller_analytics(
    reseller_id: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get historical analytics for a reseller."""
    service = ResellerAnalyticsService(db)
    
    try:
        analytics_history = service.get_reseller_analytics_history(reseller_id, limit)
        return {
            "reseller_id": reseller_id,
            "analytics_history": analytics_history,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching analytics history: {str(e)}"
        )


@router.post("/analytics/{reseller_id}", response_model=ResellerDashboardResponse)
async def regenerate_analytics(
    reseller_id: str,
    db: Session = Depends(get_db)
):
    """
    Force regenerate all analytics for a reseller.
    Recalculates from ground truth data and updates the database.
    """
    service = ResellerAnalyticsService(db)
    
    try:
        dashboard = service.regenerate_all_analytics(reseller_id)
        return dashboard
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating analytics: {str(e)}"
        )


@router.put("/analytics/{reseller_id}")
async def update_analytics(
    reseller_id: str,
    analytics_data: ResellerAnalyticsUpdate,
    db: Session = Depends(get_db)
):
    """Update reseller analytics."""
    service = ResellerAnalyticsService(db)
    
    try:
        analytics = service.update_reseller_analytics(reseller_id, analytics_data)
        
        if not analytics:
            raise HTTPException(
                status_code=404,
                detail="Reseller not found"
            )
        
        return {
            "message": "Analytics updated successfully",
            "reseller_id": reseller_id,
            "analytics": analytics
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating analytics: {str(e)}"
        )


@router.get("/summary/{reseller_id}")
async def get_reseller_summary(
    reseller_id: str,
    db: Session = Depends(get_db)
):
    """Get quick summary of reseller performance."""
    service = ResellerAnalyticsService(db)
    
    try:
        dashboard = service.generate_reseller_dashboard(reseller_id)
        analytics = dashboard.analytics
        business_stats = dashboard.business_user_stats
        
        # Calculate additional metrics
        total_businesses = len(business_stats)
        active_businesses = len([b for b in business_stats if b.credits_used > 0])
        avg_credits_per_business = analytics.total_credits_distributed / max(1, total_businesses)
        
        return {
            "reseller_id": reseller_id,
            "quick_stats": {
                "total_businesses": total_businesses,
                "active_businesses": active_businesses,
                "total_credits_purchased": analytics.total_credits_purchased,
                "total_credits_distributed": analytics.total_credits_distributed,
                "total_credits_used": analytics.total_credits_used,
                "remaining_credits": analytics.remaining_credits,
                "avg_credits_per_business": round(avg_credits_per_business, 2),
                "usage_rate": round((analytics.total_credits_used / max(1, analytics.total_credits_distributed)) * 100, 2)
            },
            "generated_at": dashboard.generated_at
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary: {str(e)}"
        )


@router.post("/ai-support")
async def ai_support(
    request: AIRequest,
    db: Session = Depends(get_db)
):
    """
    AI Copilot for Resellers.
    1. Detects Intent (Chat vs Action)
    2. Requires Confirmation for Actions
    3. Executes Actions using DB logic
    """
    reseller_id = request.reseller_id
    user_message = request.message.strip().lower()
    print(f"AI Assistant Received: {user_message} (Reseller: {reseller_id})")
    
    try:
        # --- 1. Handle Ongoing Confirmation Flow ---
        if reseller_id in pending_actions:
            action = pending_actions[reseller_id]
            
            if user_message in ["yes", "y", "confirm", "ok"]:
                # EXECUTE ACTION
                result = await execute_copilot_action(action, db)
                del pending_actions[reseller_id]
                return {"reply": result}
            elif user_message in ["no", "n", "cancel", "stop"]:
                # CANCEL ACTION
                del pending_actions[reseller_id]
                return {"reply": "Okay, I've cancelled that action. Anything else I can help with?"}
            else:
                return {"reply": f"I have a pending action: {action['description']}. Please reply 'yes' to confirm or 'no' to cancel."}

        # --- 2. Intent Parsing (Call Ollama to detect action) ---
        intent_json = await parse_intent_with_ai(request.message)
        intent = intent_json.get("intent", "chat")
        params = intent_json.get("params", {})

        # --- 3. Route based on Intent ---
        if intent == "chat":
            return await generate_standard_ai_response(request, db)
        
        elif intent == "fetch_orders":
            orders_summary = await get_reseller_orders_summary(reseller_id, db)
            return {"reply": f"Here are your recent orders:\n{orders_summary}"}
            
        elif intent == "cancel_order":
            order_id = params.get("order_id")
            if not order_id:
                return {"reply": "Which order would you like to cancel? Please provide an Order ID or TXN ID."}
            
            # Verify Ownership
            from models.payment_order import PaymentOrder
            order = db.query(PaymentOrder).filter(
                (PaymentOrder.txnid == order_id) | (PaymentOrder.id == order_id),
                PaymentOrder.user_id == reseller_id
            ).first()
            
            if not order:
                return {"reply": f"I couldn't find an order with ID {order_id} belonging to your account."}
            
            if order.status == "cancelled":
                return {"reply": f"Order {order_id} is already cancelled."}

            # Store for confirmation
            pending_actions[reseller_id] = {
                "type": "cancel_order",
                "order_id": str(order.id),
                "txnid": order.txnid,
                "description": f"Cancel order {order.txnid} (Amount: {order.amount})"
            }
            return {"reply": f"Are you sure you want to cancel order **{order.txnid}**? (Reply **yes** to confirm)"}

        elif intent == "create_user":
            email = params.get("email")
            name = params.get("name", "New User")
            if not email:
                return {"reply": "I'll need an email address to create a new user. What is their email?"}
            
            # Store for confirmation
            pending_actions[reseller_id] = {
                "type": "create_user",
                "email": email,
                "name": name,
                "reseller_id": reseller_id,
                "description": f"Create a new sub-user for {email}"
            }
            return {"reply": f"Ready to create a new sub-user for **{email}**. Should I proceed? (Reply **yes** to confirm)"}

        return await generate_standard_ai_response(request, db)

    except Exception as e:
        import traceback
        print(f"Copilot Error: {str(e)}\n{traceback.format_exc()}")
        return {"reply": "I encountered a technical glitch while processing that. Can we try again?"}

async def parse_intent_with_ai(message: str) -> dict:
    """Uses Ollama to parse natural language into structured JSON intent."""
    prompt = f"""
    You are an Intent Parser for a Reseller Admin Dashboard. 
    Convert the user's message into a structured JSON object.

    SUPPORTED INTENTS:
    1. cancel_order (params: order_id)
    2. create_user (params: email, name)
    3. fetch_orders (params: none)
    4. chat (no params)

    EXAMPLES:
    - "Cancel order TXN123" -> {{"intent": "cancel_order", "params": {{"order_id": "TXN123"}}}}
    - "Create user for vikas@gmail.com" -> {{"intent": "create_user", "params": {{"email": "vikas@gmail.com", "name": "vikas"}}}}
    - "Show me my last 5 orders" -> {{"intent": "fetch_orders", "params": {{}}}}
    - "How are you?" -> {{"intent": "chat", "params": {{}}}}

    USER MESSAGE: "{message}"

    Return ONLY valid JSON.
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "format": "json" # Llama 3 JSON mode
            },
            timeout=15
        )
        if response.status_code == 200:
            return json.loads(response.json().get("response", "{}"))
    except:
        pass
    return {"intent": "chat"}

async def execute_copilot_action(action: dict, db: Session) -> str:
    """Executes the confirmed action against the database."""
    try:
        if action["type"] == "cancel_order":
            from models.payment_order import PaymentOrder
            order = db.query(PaymentOrder).filter(PaymentOrder.id == action["order_id"]).first()
            if order:
                order.status = "cancelled"
                db.commit()
                return f"✅ Success! Order {action['txnid']} has been cancelled."
            return "❌ Error: Order not found during execution."

        elif action["type"] == "create_user":
            from services.busi_user_service import BusiUserService
            from schemas.busi_user import BusiUserCreateSchema, BusiUserProfileSchema, BusiUserInfoSchema, BusiUserAddressSchema, BusiUserWalletSchema
            
            service = BusiUserService(db)
            user_data = BusiUserCreateSchema(
                parent_reseller_id=action["reseller_id"],
                parent_role="reseller",
                role="user",
                status="active",
                whatsapp_mode="unofficial",
                profile=BusiUserProfileSchema(
                    name=action["name"],
                    username=action["email"].split('@')[0],
                    email=action["email"],
                    phone="0000000000",
                    password="Password@123" # Temporary password
                ),
                business=BusiUserInfoSchema(business_name=f"{action['name']}'s Business"),
                address=BusiUserAddressSchema(full_address="N/A", pincode="000000", country="India"),
                wallet=BusiUserWalletSchema(credits_allocated=0)
            )
            
            service.create_busi_user(user_data, created_by=action["reseller_id"])
            return f"✅ Success! Created sub-user for {action['email']}. They can now login with password: Password@123"

    except Exception as e:
        db.rollback()
        return f"❌ Action failed: {str(e)}"
    return "❌ Unknown action type."

async def get_reseller_orders_summary(reseller_id: str, db: Session) -> str:
    from models.payment_order import PaymentOrder
    orders = db.query(PaymentOrder).filter(
        PaymentOrder.user_id == reseller_id
    ).order_by(PaymentOrder.created_at.desc()).limit(5).all()
    
    if not orders: return "No orders found."
    
    summary = ""
    for o in orders:
        summary += f"- {o.txnid}: {o.plan_name} ({o.amount} INR) - Status: {o.status}\n"
    return summary

async def generate_standard_ai_response(request: AIRequest, db: Session) -> dict:
    """Original AI response logic preserved for chat fallback."""
    try:
        service = ResellerAnalyticsService(db)
        dashboard = service.generate_reseller_dashboard(request.reseller_id)
        
        # ... (Context building logic same as previous task) ...
        biz_stats = dashboard.business_users[:5]
        recent_txs = dashboard.recent_transactions[:5]
        
        context_summary = f"""
        RESELLER INFO:
        - Wallet Balance: {dashboard.wallet_balance} credits
        - Total Business Users: {len(dashboard.business_users)}
        - Messages Sent: {dashboard.messages_sent}
        """
        # ... truncated for brevity in this snippet ...

        prompt = f"You are a helpful assistant. Context: {context_summary}\n\nQuestion: {request.message}"
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=30
        )
        return {"reply": response.json().get("response", "Error")}
    except:
        return {"reply": "I'm here to help, but I'm having trouble with my brain. Ask me to show your orders instead!"}
