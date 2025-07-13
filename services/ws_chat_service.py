import json
from datetime import datetime
from models.db_tables import Message
from pydantic import BaseModel, ValidationError
from models.schema import WSMessage
from core.redis import RedisCoupleHistory

async def process_ws_connect(db, manager, user_id, websocket):
    await manager.connect(user_id, websocket)
    manager.auto_register_from_redis(user_id)
    await manager.broadcast_status(user_id, "online")
    await send_undelivered_messages(db, manager, user_id, websocket)

async def process_ws_disconnect(manager, user_id):
    manager.disconnect(user_id)
    await manager.broadcast_status(user_id, "offline")

async def process_ws_message(db, manager, user_id, websocket, data):
    try:
        message_data = WSMessage.parse_raw(data)
    except ValidationError as e:
        await websocket.send_json({"type": "error", "message": f"잘못된 메시지 형식: {e}"})
        return

    handler_map = {
        "register_couple": handle_register_couple,
        "message": handle_send_message,
    }
    handler = handler_map.get(message_data.type)
    if handler:
        await handler(db, manager, user_id, websocket, message_data)
    else:
        await websocket.send_json({"type": "error", "message": "알 수 없는 타입"})

async def send_undelivered_messages(db, manager, user_id, websocket):
    couple_id = manager.get_couple_id(user_id)
    partner_id = manager.get_partner(user_id)
    if not partner_id or not couple_id:
        return
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

async def handle_register_couple(db, manager, user_id, websocket, data):
    partner_id = data.partner_id
    couple_id = data.couple_id
    if not partner_id or not couple_id:
        await websocket.send_json({"type": "error", "message": "partner_id, couple_id 필요"})
        return
    manager.register_couple(user_id, partner_id, couple_id)
    if manager.is_user_connected(partner_id):
        await websocket.send_json({"type": "system", "message": f"{partner_id}와 연결되었습니다."})
        await manager.send_personal_json({"type": "system", "message": f"{user_id}와 연결되었습니다."}, partner_id)

async def handle_send_message(db, manager, user_id, websocket, data):
    couple_id = data.couple_id
    message = data.message
    image_url = data.image_url
    partner_id = manager.get_partner(user_id)
    created_at = datetime.utcnow()
    db_msg = Message(
        couple_id=couple_id,
        user_id=user_id,
        content=message,
        image_url=image_url,
        has_image=bool(image_url),
        created_at=created_at,
        is_delivered=manager.is_user_connected(partner_id)
    )
    try:
        db.add(db_msg)
        db.commit()
        # Redis에 append (DB 성공 이후에만)
        
        RedisCoupleHistory.append(
            couple_id,
            {
                "user_id": user_id,
                "content": message,
                "image_url": image_url,
                "created_at": created_at.isoformat()
            }
        )
        # 상대 연결되어 있으면 바로 전달
        if manager.is_user_connected(partner_id):
            await manager.send_personal_message(json.dumps({
                "type": "message",
                "from": user_id,
                "couple_id": couple_id,
                "message": message,
                "image_url": image_url,
                "created_at": created_at.isoformat()
            }), partner_id)
    except Exception as e:
        db.rollback()
        await websocket.send_json({"type": "error", "message": f"메시지 저장 오류: {e}"})
    finally:
        db.close()