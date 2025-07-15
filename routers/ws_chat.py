from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi import APIRouter
from core.dependencies import get_connection_manager, get_db_session
from services.ws_chat_service import (
    process_ws_connect,
    process_ws_message,
    process_ws_disconnect
)

router = APIRouter()

@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    manager = Depends(get_connection_manager),
    db = Depends(get_db_session)
):
    try:
        await process_ws_connect(db, manager, user_id, websocket)
        while True:
            data = await websocket.receive_text()
            await process_ws_message(db, manager, user_id, websocket, data)
    except WebSocketDisconnect:
        await process_ws_disconnect(manager, user_id)
    finally:
        db.close()
