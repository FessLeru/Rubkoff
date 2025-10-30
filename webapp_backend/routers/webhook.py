"""
Telegram webhook router for API
"""
import logging
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle Telegram webhook updates
    """
    try:
        # Get the raw body
        body = await request.body()
        
        if not body:
            logger.warning("Received empty webhook body")
            return JSONResponse({"status": "ok"})
        
        # Parse JSON
        try:
            update_data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Log the update (for debugging)
        logger.info(f"Received webhook update: {update_data.get('update_id', 'unknown')}")
        
        # Here would be the actual bot update processing
        # For now, just return success
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/webhook")
async def webhook_info():
    """
    Get webhook information
    """
    return {
        "message": "Telegram Webhook Endpoint",
        "status": "ready",
        "method": "POST",
        "description": "Send Telegram updates to this endpoint"
    }


@router.get("/webhook/health")
async def webhook_health():
    """
    Webhook health check
    """
    return {
        "status": "healthy",
        "endpoint": "/webhook",
        "ready": True
    } 