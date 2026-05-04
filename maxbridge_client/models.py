from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class User:
    id: int
    name: str
    username: Optional[str] = None
    avatar: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "User":
        contact_id = int(raw.get("id", 0))
        names = raw.get("names") or []
        name = names[0].get("name") if names else str(contact_id)
        username = raw.get("username")
        avatar = raw.get("baseUrl") or raw.get("baseRawUrl")
        return cls(id=contact_id, name=name, username=username, avatar=avatar)


@dataclass
class Chat:
    id: int
    title: str
    type: str
    participants_count: Optional[int] = None
    avatar: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "Chat":
        chat_id = int(raw.get("id", 0))
        chat_type = str(raw.get("type", "UNKNOWN"))
        participants = raw.get("participants") or {}
        title = raw.get("title") or ""
        return cls(
            id=chat_id,
            title=title,
            type=chat_type,
            participants_count=len(participants) or None,
            avatar=raw.get("avatar") or raw.get("baseUrl") or raw.get("baseRawUrl"),
        )


@dataclass
class Message:
    id: str
    chat_id: int
    user_id: int
    text: str
    timestamp: int
    attaches: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any], chat_id: Optional[int] = None) -> "Message":
        resolved_chat_id = chat_id if chat_id is not None else int(raw.get("chatId", 0))
        return cls(
            id=str(raw.get("id", "")),
            chat_id=resolved_chat_id,
            user_id=int(raw.get("sender", 0)),
            text=str(raw.get("text", "")),
            timestamp=int(raw.get("time", 0)),
            attaches=list(raw.get("attaches") or []),
        )
