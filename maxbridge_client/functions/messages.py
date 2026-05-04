from pathlib import Path
from random import randint
from typing import Any, Dict, List, Optional, Union

from ..client import MaxClient
from .uploads import upload_file, upload_photo

MessageId = Union[str, int]


async def send_message(
    client: MaxClient,
    chat_id: int,
    text: str,
    notify: bool = True,
    reply_to: Optional[MessageId] = None,
    attaches: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    message: Dict[str, Any] = {
        "text": text,
        "cid": randint(1750000000000, 2000000000000),
        "elements": [],
        "attaches": attaches or [],
    }
    if reply_to is not None:
        message["link"] = {"type": "REPLY", "messageId": str(reply_to)}
    return await client.invoke_method(
        opcode=64,
        payload={"chatId": chat_id, "message": message, "notify": notify},
    )


async def edit_message(
    client: MaxClient,
    chat_id: int,
    message_id: MessageId,
    text: str,
    attaches: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=67,
        payload={
            "chatId": chat_id,
            "messageId": str(message_id),
            "text": text,
            "elements": [],
            "attaches": attaches or [],
        },
    )


async def delete_message(
    client: MaxClient,
    chat_id: int,
    message_ids: List[MessageId],
    delete_for_me: bool = False,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=66,
        payload={
            "chatId": chat_id,
            "messageIds": [str(message_id) for message_id in message_ids],
            "forMe": delete_for_me,
        },
    )


async def pin_message(
    client: MaxClient,
    chat_id: int,
    message_id: MessageId,
    notify: bool = False,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=55,
        payload={"chatId": chat_id, "notifyPin": notify, "messageId": str(message_id)},
    )


async def reply_message(
    client: MaxClient,
    chat_id: int,
    text: str,
    reply_to_message_id: MessageId,
    notify: bool = True,
) -> Dict[str, Any]:
    return await send_message(
        client=client,
        chat_id=chat_id,
        text=text,
        notify=notify,
        reply_to=reply_to_message_id,
    )


async def send_photo(
    client: MaxClient,
    chat_id: int,
    image_path: str,
    caption: str = "",
    notify: bool = True,
) -> Dict[str, Any]:
    path = Path(image_path)
    with path.open("rb") as stream:
        photo = await upload_photo(client, chat_id, stream, filename=path.name)
    return await send_message(
        client=client,
        chat_id=chat_id,
        text=caption,
        notify=notify,
        attaches=[photo],
    )


async def send_file(
    client: MaxClient,
    chat_id: int,
    file_path: str,
    caption: str = "",
    notify: bool = True,
) -> Dict[str, Any]:
    path = Path(file_path)
    with path.open("rb") as stream:
        file_attachment = await upload_file(
            client,
            chat_id,
            stream,
            filename=path.name,
        )
    return await send_message(
        client=client,
        chat_id=chat_id,
        text=caption,
        notify=notify,
        attaches=[file_attachment],
    )
