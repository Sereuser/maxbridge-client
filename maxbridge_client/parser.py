from dataclasses import dataclass
from typing import Any, Dict, Optional

from .models import Message


@dataclass(frozen=True)
class MessageEvent:
    chat_id: int
    message: Message
    raw: Dict[str, Any]


@dataclass(frozen=True)
class UploadEvent:
    file_id: Optional[int]
    video_id: Optional[int]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class PacketEnvelope:
    ver: Optional[int]
    cmd: Optional[int]
    opcode: Optional[int]
    seq: Optional[int]
    payload: Dict[str, Any]
    raw: Dict[str, Any]
    message_event: Optional[MessageEvent] = None
    upload_event: Optional[UploadEvent] = None


def parse_packet(packet: Dict[str, Any]) -> PacketEnvelope:
    payload = packet.get("payload") or {}
    message_event: Optional[MessageEvent] = None
    upload_event: Optional[UploadEvent] = None

    if packet.get("opcode") == 64 and isinstance(payload.get("message"), dict):
        raw_message = dict(payload["message"])
        chat_id = int(payload.get("chatId") or raw_message.get("chatId") or 0)
        raw_message.setdefault("chatId", chat_id)
        message_event = MessageEvent(
            chat_id=chat_id,
            message=Message.from_raw(raw_message, chat_id=chat_id),
            raw=raw_message,
        )

    if packet.get("opcode") == 136:
        file_id = payload.get("fileId")
        video_id = payload.get("videoId")
        upload_event = UploadEvent(
            file_id=int(file_id) if file_id is not None else None,
            video_id=int(video_id) if video_id is not None else None,
            raw=payload,
        )

    return PacketEnvelope(
        ver=packet.get("ver"),
        cmd=packet.get("cmd"),
        opcode=packet.get("opcode"),
        seq=packet.get("seq"),
        payload=payload,
        raw=packet,
        message_event=message_event,
        upload_event=upload_event,
    )
