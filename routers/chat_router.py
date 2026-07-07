from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, UTC
import redis
from database import get_db
from auth.auth_dependency import check_current_user
from auth.auth_security import decode_access_token
from connection_manager import manager
from sqlalchemy import or_
from sqlalchemy.orm import aliased
from typing import List
import models

router = APIRouter()

r = redis.Redis(host="localhost", port=6379, decode_responses=True)


@router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    # 1. Token verify karo, accept karne se pehle
    payload = decode_access_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload["userId"]

    await manager.connect(user_id, websocket)
    r.set(f"online:{user_id}", "1")
    r.incr(f"online_count:{user_id}")

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except (ValueError, TypeError):
                await websocket.send_json({"error": "Invalid JSON"})
                continue
            msg_type = data.get("type", "message")
            if msg_type == "typing":
                receiver_id = data.get("receiver_id")
                if receiver_id:
                    await manager.send_personal_message(receiver_id, f"typing:{user_id}")
                    continue
            try:
                receiver_id = data["receiver_id"]
                content = data["content"]
            except (KeyError, ValueError, TypeError):
                await websocket.send_json({"error": "Invalid message format"})
                continue

            MAX_MESSAGE_LENGTH = 20

            if len(content) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({"error": f"Message {MAX_MESSAGE_LENGTH} characters se zyada nahi ho sakta"})
                continue

            if not content or not content.strip():
                await websocket.send_json({"error": "Message khali nahi ho sakta"})
                continue

            if receiver_id == user_id:
                await websocket.send_json({"error": "Aap khud ko message nahi bhej sakte"})
                continue

            receiver_exists = db.query(models.User).filter(models.User.id == receiver_id).first()
            if not receiver_exists:
                await websocket.send_json({"error": "Receiver nahi mila"})
                continue

            new_message = models.Chat(
                sender_id=user_id,
                receiver_id=receiver_id,
                content=content,
                timestamp=datetime.now(UTC),
                is_read=False
            )
            db.add(new_message)
            db.commit()

            message_payload = f"{user_id}:{content}"
            delivered = await manager.send_personal_message(receiver_id, message_payload)

            if not delivered:
                r.publish(f"chat_notifications:{receiver_id}", message_payload)
            
            await manager.send_to_other_devices(user_id, websocket, message_payload)

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        remaining = r.decr(f"online_count:{user_id}")
        if remaining <= 0:
            r.delete(f"online_count:{user_id}")
            r.delete(f"online:{user_id}")

    except Exception:
        manager.disconnect(user_id, websocket)
        remaining = r.decr(f"online_count:{user_id}")
        if remaining <= 0:
            r.delete(f"online_count:{user_id}")
            r.delete(f"online:{user_id}")
        raise
    


@router.get("/chat/status/{user_id}")
def check_online_status(user_id: int, current_user: dict = Depends(check_current_user)):
    is_online = r.exists(f"online:{user_id}")
    return {"user_id": user_id, "online": bool(is_online)}

@router.get("/chat/history/{other_user_id}")
def get_chat_history(
    other_user_id: int,
    before_id: int | None = Query(default=None, description="Is ID se pehle ke messages lao (pagination cursor)"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_current_user)
):
    my_id = current_user["userId"]

    sent_condition = (models.Chat.sender_id == my_id) & (models.Chat.receiver_id == other_user_id)
    received_condition = (models.Chat.sender_id == other_user_id) & (models.Chat.receiver_id == my_id)

    SenderUser = aliased(models.User)
    ReceiverUser = aliased(models.User)

    query = (
        db.query(models.Chat, SenderUser.username, ReceiverUser.username)
        .join(SenderUser, models.Chat.sender_id == SenderUser.id)
        .join(ReceiverUser, models.Chat.receiver_id == ReceiverUser.id)
        .filter(or_(sent_condition, received_condition))
    )

    if before_id is not None:
        query = query.filter(models.Chat.id < before_id)

    rows = query.order_by(models.Chat.id.desc()).limit(limit).all()

    messages_data = [
        {
            "id": chat.id,
            "sender_id": chat.sender_id,
            "sender_username": sender_username,
            "receiver_id": chat.receiver_id,
            "receiver_username": receiver_username,
            "content": chat.content,
            "timestamp": chat.timestamp,
            "is_read": chat.is_read,
        }
        for chat, sender_username, receiver_username in reversed(rows)
    ]

    next_cursor = messages_data[0]["id"] if messages_data else None

    return {
        "limit": limit,
        "next_cursor": next_cursor,
        "messages": messages_data,
    }


@router.patch("/chat/mark-read/{sender_id}")
async def mark_messages_read(sender_id: int, db: Session = Depends(get_db), current_user: dict = Depends(check_current_user)):
    my_id = current_user["userId"]
    updated_count = db.query(models.Chat).filter(
        models.Chat.sender_id == sender_id,
        models.Chat.receiver_id == my_id,
        models.Chat.is_read == False
    ).update({"is_read": True})
    db.commit()

    if updated_count > 0:
        # sender ko real-time batao ki uske messages padh liye gaye
        await manager.send_personal_message(sender_id, f"read_receipt:{my_id}")

    return {"status": "marked as read", "updated_count": updated_count}



@router.get("/chat/unread-counts")
def get_unread_counts(db: Session = Depends(get_db), current_user: dict = Depends(check_current_user)):
    my_id = current_user["userId"]

    results = (
        db.query(models.Chat.sender_id, func.count(models.Chat.id))
        .filter(models.Chat.receiver_id == my_id, models.Chat.is_read == False)
        .group_by(models.Chat.sender_id)
        .all()
    )

    return {
        "unread_counts": [
            {"sender_id": sender_id, "unread_count": count}
            for sender_id, count in results
        ]
    }