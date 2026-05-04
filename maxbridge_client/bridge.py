import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .models import Message
from .parser import PacketEnvelope, parse_packet


@dataclass(frozen=True)
class BridgeSender:
    user_id: int
    display_name: Optional[str]
    username: Optional[str]
    avatar_url: Optional[str]
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BridgeChat:
    chat_id: int
    chat_type: Optional[str]
    title: Optional[str]
    peer_user_id: Optional[int]
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BridgeAttachment:
    kind: str
    attachment_id: Optional[str]
    token: Optional[str]
    url: Optional[str]
    mime_type: Optional[str]
    name: Optional[str]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class BridgeContent:
    kind: str
    text: str
    options: List[Any] = field(default_factory=list)
    reaction_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_options(self) -> bool:
        return bool(self.options)

    @property
    def is_textual(self) -> bool:
        return self.kind == "text" or bool(self.text)


@dataclass(frozen=True)
class BridgeMessage:
    message_id: str
    event_id: str
    dedupe_key: str
    chat_id: int
    sender_id: int
    sender: Optional[BridgeSender]
    chat: Optional[BridgeChat]
    content: BridgeContent
    timestamp: int
    reply_to_message_id: Optional[str]
    attachments: List[BridgeAttachment] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.content.text

    @property
    def is_empty(self) -> bool:
        return not self.text and not self.attachments and not self.content.has_options

    @property
    def normalized_text(self) -> str:
        if self.text:
            return self.text
        if self.content.has_options:
            return " | ".join(str(option) for option in self.content.options)
        return ""


@dataclass(frozen=True)
class BridgeEvent:
    kind: str
    event_id: str
    dedupe_key: str
    opcode: Optional[int]
    seq: Optional[int]
    chat_id: Optional[int]
    message: Optional[BridgeMessage]
    upload: Optional[Dict[str, Optional[int]]]
    raw: Dict[str, Any]


@dataclass
class BridgeEventLedger:
    max_size: int = 10000
    seen_event_ids: Set[str] = field(default_factory=set)
    seen_dedupe_keys: Set[str] = field(default_factory=set)
    _order: Deque[Tuple[str, str]] = field(default_factory=deque)

    def register(self, event: BridgeEvent) -> bool:
        if event.event_id in self.seen_event_ids or event.dedupe_key in self.seen_dedupe_keys:
            return False
        self.seen_event_ids.add(event.event_id)
        self.seen_dedupe_keys.add(event.dedupe_key)
        self._order.append((event.event_id, event.dedupe_key))
        self._trim()
        return True

    def contains(self, event: BridgeEvent) -> bool:
        return event.event_id in self.seen_event_ids or event.dedupe_key in self.seen_dedupe_keys

    def reset(self) -> None:
        self.seen_event_ids.clear()
        self.seen_dedupe_keys.clear()
        self._order.clear()

    def _trim(self) -> None:
        while len(self._order) > self.max_size:
            event_id, dedupe_key = self._order.popleft()
            self.seen_event_ids.discard(event_id)
            self.seen_dedupe_keys.discard(dedupe_key)
        if len(self.seen_event_ids) <= self.max_size and len(self.seen_dedupe_keys) <= self.max_size:
            return


@dataclass(frozen=True)
class BridgeRoomMapping:
    max_chat_id: int
    matrix_room_id: str
    bridge_kind: str
    last_event_id: Optional[str] = None
    last_dedupe_key: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeRoomRegistry:
    mappings: Dict[int, BridgeRoomMapping] = field(default_factory=dict)

    def bind(self, mapping: BridgeRoomMapping) -> None:
        self.mappings[mapping.max_chat_id] = mapping

    def resolve(self, max_chat_id: int) -> Optional[BridgeRoomMapping]:
        return self.mappings.get(max_chat_id)

    def unbind(self, max_chat_id: int) -> None:
        self.mappings.pop(max_chat_id, None)

    def values(self) -> List[BridgeRoomMapping]:
        return list(self.mappings.values())


def build_bridge_sender(raw_user: Optional[Dict[str, Any]]) -> Optional[BridgeSender]:
    if not raw_user:
        return None
    names = raw_user.get("names") or []
    display_name = None
    if names and isinstance(names[0], dict):
        display_name = _pick_string(names[0], "name", "firstName")
    return BridgeSender(
        user_id=int(raw_user.get("id", 0)),
        display_name=display_name,
        username=_pick_string(raw_user, "username"),
        avatar_url=_pick_string(raw_user, "baseUrl", "baseRawUrl"),
        raw=dict(raw_user),
    )


def build_bridge_chat(
    raw_chat: Optional[Dict[str, Any]],
    current_user_id: Optional[int] = None,
) -> Optional[BridgeChat]:
    if not raw_chat:
        return None
    peer_user_id = None
    participants = raw_chat.get("participants") or {}
    if str(raw_chat.get("type")) == "DIALOG":
        for user_id in participants.keys():
            try:
                normalized = int(user_id)
            except (TypeError, ValueError):
                continue
            if current_user_id is not None and normalized == current_user_id:
                continue
            peer_user_id = normalized
            break
    return BridgeChat(
        chat_id=int(raw_chat.get("id", 0)),
        chat_type=_pick_string(raw_chat, "type"),
        title=_pick_string(raw_chat, "title"),
        peer_user_id=peer_user_id,
        raw=dict(raw_chat),
    )


def build_bridge_attachment(raw: Dict[str, Any]) -> BridgeAttachment:
    return BridgeAttachment(
        kind=str(raw.get("_type") or raw.get("type") or "UNKNOWN"),
        attachment_id=_pick_attachment_id(raw),
        token=_pick_string(raw, "token", "photoToken"),
        url=_pick_string(raw, "url", "downloadUrl"),
        mime_type=_pick_string(raw, "mimeType", "mime"),
        name=_pick_string(raw, "name", "fileName"),
        raw=dict(raw),
    )


def build_bridge_content(raw_message: Dict[str, Any]) -> BridgeContent:
    text = str(raw_message.get("text", ""))
    options_value = raw_message.get("options")
    if isinstance(options_value, list):
        options = list(options_value)
    elif options_value is None:
        options = []
    else:
        options = [options_value]
    reaction_info = raw_message.get("reactionInfo")
    metadata = {
        key: value
        for key, value in raw_message.items()
        if key not in {"text", "attaches", "link", "options", "reactionInfo"}
    }
    if text:
        kind = "text"
    elif options:
        kind = "options"
    elif reaction_info is not None:
        kind = "reaction"
    elif raw_message.get("attaches"):
        kind = "attachment"
    else:
        kind = "unknown"
    return BridgeContent(
        kind=kind,
        text=text,
        options=options,
        reaction_info=dict(reaction_info) if isinstance(reaction_info, dict) else None,
        metadata=metadata,
    )


def build_bridge_message(
    raw_message: Dict[str, Any],
    chat_id: Optional[int] = None,
    sender: Optional[BridgeSender] = None,
    chat: Optional[BridgeChat] = None,
) -> BridgeMessage:
    resolved_chat_id = chat_id if chat_id is not None else int(raw_message.get("chatId", 0))
    sender_id = int(raw_message.get("sender", 0))
    message_id = str(raw_message.get("id", ""))
    attachments = [
        build_bridge_attachment(attachment)
        for attachment in raw_message.get("attaches", [])
        if isinstance(attachment, dict)
    ]
    link = raw_message.get("link") or {}
    reply_to_message_id = None
    if isinstance(link, dict):
        reply_to_message_id = _pick_string(link, "messageId")
    event_id = make_event_id(resolved_chat_id, message_id)
    content = build_bridge_content(raw_message)
    return BridgeMessage(
        message_id=message_id,
        event_id=event_id,
        dedupe_key=make_message_dedupe_key(
            resolved_chat_id,
            sender_id,
            int(raw_message.get("time", 0)),
            message_id,
        ),
        chat_id=resolved_chat_id,
        sender_id=sender_id,
        sender=sender,
        chat=chat,
        content=content,
        timestamp=int(raw_message.get("time", 0)),
        reply_to_message_id=reply_to_message_id,
        attachments=attachments,
        raw=dict(raw_message),
    )


def build_bridge_event(
    packet: Dict[str, Any],
    sender: Optional[BridgeSender] = None,
    chat: Optional[BridgeChat] = None,
) -> BridgeEvent:
    parsed = parse_packet(packet)
    message = (
        build_bridge_message(
            parsed.message_event.raw,
            chat_id=parsed.message_event.chat_id,
            sender=sender,
            chat=chat,
        )
        if parsed.message_event is not None
        else None
    )
    upload = None
    event_id = make_packet_event_id(parsed.opcode, parsed.seq)
    dedupe_key = event_id
    if parsed.upload_event is not None:
        upload = {
            "file_id": parsed.upload_event.file_id,
            "video_id": parsed.upload_event.video_id,
        }
        event_id = make_upload_event_id(
            parsed.upload_event.file_id,
            parsed.upload_event.video_id,
            parsed.seq,
        )
        dedupe_key = event_id
    kind = "unknown"
    chat_id = None
    if message is not None:
        kind = "message"
        event_id = message.event_id
        dedupe_key = message.dedupe_key
        chat_id = message.chat_id
    elif upload is not None:
        kind = "upload"
    return BridgeEvent(
        kind=kind,
        event_id=event_id,
        dedupe_key=dedupe_key,
        opcode=parsed.opcode,
        seq=parsed.seq,
        chat_id=chat_id,
        message=message,
        upload=upload,
        raw=dict(packet),
    )


class BridgeEventStream(AsyncIterator[BridgeEvent]):
    def __init__(
        self,
        client: Any,
        include_self: bool = True,
        include_non_message: bool = False,
        allowed_kinds: Optional[Sequence[str]] = None,
        max_queue_size: int = 0,
        ledger: Optional[BridgeEventLedger] = None,
    ) -> None:
        self._client = client
        self._include_self = include_self
        self._include_non_message = include_non_message
        self._allowed_kinds: Optional[Set[str]] = set(allowed_kinds) if allowed_kinds else None
        self._ledger = ledger
        self._queue: asyncio.Queue[BridgeEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._started = False
        self._closed = False

    def start(self) -> "BridgeEventStream":
        if not self._started:
            self._client.add_parsed_packet_listener(self._on_packet)
            self._started = True
        return self

    async def _on_packet(self, client: Any, packet: PacketEnvelope) -> None:
        if self._closed:
            return
        event = client.to_bridge_event(packet.raw)
        if self._ledger is not None and not self._ledger.register(event):
            return
        if not self._include_non_message and event.message is None:
            return
        if self._allowed_kinds is not None and event.kind not in self._allowed_kinds:
            return
        if not self._include_self and event.message is not None:
            profile_id = (client.profile or {}).get("contact", {}).get("id")
            if profile_id is not None and event.message.sender_id == profile_id:
                return
        await self._queue.put(event)

    def close(self) -> None:
        if self._started:
            self._client.remove_parsed_packet_listener(self._on_packet)
        self._closed = True

    def __aiter__(self) -> "BridgeEventStream":
        return self.start()

    async def __anext__(self) -> BridgeEvent:
        if self._closed and self._queue.empty():
            raise StopAsyncIteration
        return await self._queue.get()


def bridge_message_from_model(message: Message) -> BridgeMessage:
    return build_bridge_message(
        {
            "id": message.id,
            "chatId": message.chat_id,
            "sender": message.user_id,
            "text": message.text,
            "time": message.timestamp,
            "attaches": message.attaches,
        }
    )


def make_event_id(chat_id: int, message_id: str) -> str:
    return f"max:message:{chat_id}:{message_id}"


def make_message_dedupe_key(
    chat_id: int, sender_id: int, timestamp: int, message_id: str
) -> str:
    return f"max:dedupe:{chat_id}:{sender_id}:{timestamp}:{message_id}"


def make_packet_event_id(opcode: Optional[int], seq: Optional[int]) -> str:
    return f"max:packet:{opcode or 0}:{seq or 0}"


def make_upload_event_id(
    file_id: Optional[int], video_id: Optional[int], seq: Optional[int]
) -> str:
    return f"max:upload:{file_id or 0}:{video_id or 0}:{seq or 0}"


def normalize_bridge_history(items: Iterable[Dict[str, Any]], chat_id: int) -> List[BridgeMessage]:
    return [build_bridge_message(item, chat_id=chat_id) for item in items]


def _pick_attachment_id(raw: Dict[str, Any]) -> Optional[str]:
    return _pick_string(raw, "fileId", "videoId", "photoId", "id")


def _pick_string(raw: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = raw.get(key)
        if value is not None:
            return str(value)
    return None
