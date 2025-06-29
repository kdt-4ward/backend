from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from core.connection_manager import ConnectionManager
from core.dependencies import get_connection_manager
from core.db import SessionLocal
from models.db_models import Message
from config import router
import json
from datetime import datetime

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    manager: ConnectionManager = Depends(get_connection_manager)
):
    await manager.connect(user_id, websocket)
    manager.auto_register_from_redis(user_id)  # 👈 자동 등록
    await manager.broadcast_status(user_id, "online")

    db = SessionLocal()

    try:
        couple_id = manager.get_couple_id(user_id)
        partner_id = manager.get_partner(user_id)

        # ✅ 미전달 메시지 전송
        if partner_id and couple_id:
            undelivered = db.query(Message).filter_by(
                couple_id=couple_id,
                user_id=partner_id,
                is_delivered=False
            ).order_by(Message.created_at).all()

            for msg in undelivered:
                await websocket.send_json({
                    "type": "message",
                    "from": msg.user_id,
                    "couple_id": msg.couple_id,
                    "message": msg.content,
                    "image_url": msg.image_url
                })
                msg.is_delivered = True
            db.commit()

        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # 커플 등록 처리
            if message_data["type"] == "register_couple":
                partner_id = message_data["partner_id"]
                couple_id = message_data["couple_id"]

                manager.register_couple(user_id, partner_id, couple_id)

                if manager.is_couple_ready(user_id):
                    await websocket.send_json({
                        "type": "system",
                        "message": f"{partner_id}와 연결되었습니다."
                    })
                    await manager.send_personal_json({
                        "type": "system",
                        "message": f"{user_id}와 연결되었습니다."
                    }, partner_id)

            elif message_data["type"] == "message":
                couple_id = message_data["couple_id"]
                message = message_data.get("message")
                image_url = message_data.get("image_url")
                partner_id = manager.get_partner(user_id)

                db_msg = Message(
                    couple_id=couple_id,
                    user_id=user_id,
                    content=message,
                    image_url=image_url,
                    has_image=bool(image_url),
                    created_at=datetime.utcnow(),
                    is_delivered=manager.is_user_connected(partner_id)
                )
                db.add(db_msg)
                db.commit()

                if manager.is_user_connected(partner_id):
                    await manager.send_personal_message(json.dumps({
                        "type": "message",
                        "from": user_id,
                        "couple_id": couple_id,
                        "message": message,
                        "image_url": image_url
                    }), partner_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await manager.broadcast_status(user_id, "offline")
    finally:
        db.close()
