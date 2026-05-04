from dataclasses import dataclass
from typing import List, Optional

from .bridge import BridgeMessage


@dataclass(frozen=True)
class BridgeCheckpoint:
    chat_id: int
    last_message_id: str
    last_event_id: str
    last_dedupe_key: str
    last_timestamp: int


@dataclass(frozen=True)
class BridgeBackfillPage:
    chat_id: int
    messages: List[BridgeMessage]
    checkpoint: Optional[BridgeCheckpoint]

    @property
    def has_messages(self) -> bool:
        return bool(self.messages)


def checkpoint_from_message(chat_id: int, message: BridgeMessage) -> BridgeCheckpoint:
    return BridgeCheckpoint(
        chat_id=chat_id,
        last_message_id=message.message_id,
        last_event_id=message.event_id,
        last_dedupe_key=message.dedupe_key,
        last_timestamp=message.timestamp,
    )


def advance_checkpoint(
    checkpoint: Optional[BridgeCheckpoint], messages: List[BridgeMessage], chat_id: int
) -> Optional[BridgeCheckpoint]:
    if not messages:
        return checkpoint
    latest = max(messages, key=lambda message: (message.timestamp, message.message_id))
    return checkpoint_from_message(chat_id, latest)


def build_backfill_page(chat_id: int, messages: List[BridgeMessage]) -> BridgeBackfillPage:
    ordered = sorted(messages, key=lambda message: (message.timestamp, message.message_id))
    return BridgeBackfillPage(
        chat_id=chat_id,
        messages=ordered,
        checkpoint=advance_checkpoint(None, ordered, chat_id),
    )
