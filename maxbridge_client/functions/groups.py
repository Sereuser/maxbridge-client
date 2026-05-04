from random import randint
from typing import Any, Dict, List, Optional

from ..client import MaxClient


def _resolve_admin_permissions(
    deleting_messages: bool,
    control_participants: bool,
    control_admins: bool,
) -> int:
    if deleting_messages and control_participants and control_admins:
        return 255
    if not deleting_messages and control_participants and control_admins:
        return 254
    if deleting_messages and control_participants and not control_admins:
        return 251
    if not deleting_messages and control_participants and not control_admins:
        return 250
    if deleting_messages and not control_participants and control_admins:
        return 125
    if not deleting_messages and not control_participants and control_admins:
        return 124
    if deleting_messages and not control_participants and not control_admins:
        return 121
    return 120


async def create_group(
    client: MaxClient, group_name: str, participant_ids: List[int]
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=64,
        payload={
            "message": {
                "cid": randint(1750000000000, 2000000000000),
                "attaches": [
                    {
                        "_type": "CONTROL",
                        "event": "new",
                        "chatType": "CHAT",
                        "title": group_name,
                        "userIds": participant_ids,
                    }
                ],
            },
            "notify": True,
        },
    )


async def invite_users(
    client: MaxClient,
    group_id: int,
    participant_ids: List[int],
    show_history: bool = True,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=77,
        payload={
            "chatId": group_id,
            "userIds": participant_ids,
            "showHistory": show_history,
            "operation": "add",
        },
    )


async def remove_users(
    client: MaxClient,
    group_id: int,
    participant_ids: List[int],
    delete_messages: bool = False,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=77,
        payload={
            "chatId": group_id,
            "userIds": participant_ids,
            "operation": "remove",
            "cleanMsgPeriod": -1 if delete_messages else 0,
        },
    )


async def add_admin(
    client: MaxClient,
    group_id: int,
    admin_ids: List[int],
    deleting_messages: bool = False,
    control_participants: bool = False,
    control_admins: bool = False,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=77,
        payload={
            "chatId": group_id,
            "userIds": admin_ids,
            "type": "ADMIN",
            "operation": "add",
            "permissions": _resolve_admin_permissions(
                deleting_messages=deleting_messages,
                control_participants=control_participants,
                control_admins=control_admins,
            ),
        },
    )


async def remove_admin(
    client: MaxClient, group_id: int, admin_ids: List[int]
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=77,
        payload={
            "chatId": group_id,
            "userIds": admin_ids,
            "type": "ADMIN",
            "operation": "remove",
        },
    )


async def transfer_group_ownership(
    client: MaxClient, group_id: int, new_owner_id: int
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=55,
        payload={"chatId": group_id, "changeOwnerId": new_owner_id},
    )


async def change_group_settings(
    client: MaxClient,
    group_id: int,
    all_can_pin_message: bool = False,
    only_owner_can_change_icon_title: bool = True,
    only_admin_can_add_member: bool = True,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=55,
        payload={
            "chatId": group_id,
            "options": {
                "ONLY_OWNER_CAN_CHANGE_ICON_TITLE": only_owner_can_change_icon_title,
                "ALL_CAN_PIN_MESSAGE": all_can_pin_message,
                "ONLY_ADMIN_CAN_ADD_MEMBER": only_admin_can_add_member,
            },
        },
    )


async def change_group_profile(
    client: MaxClient,
    group_id: int,
    new_group_name: Optional[str] = None,
    new_description: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"chatId": group_id}
    if new_group_name is not None:
        payload["theme"] = new_group_name
    if new_description is not None:
        payload["description"] = new_description
    return await client.invoke_method(opcode=55, payload=payload)


async def get_group_members(
    client: MaxClient, group_id: int, marker: int = 0, count: int = 500
) -> Dict[str, Any]:
    if count > 500:
        raise ValueError("Maximum supported count is 500.")
    return await client.invoke_method(
        opcode=59,
        payload={"type": "MEMBER", "marker": marker, "chatId": group_id, "count": count},
    )


async def resolve_group_by_link(client: MaxClient, link_hash: str) -> Dict[str, Any]:
    return await client.invoke_method(opcode=89, payload={"link": f"join/{link_hash}"})


async def join_group_by_link(client: MaxClient, link_hash: str) -> Dict[str, Any]:
    return await client.invoke_method(opcode=57, payload={"link": f"join/{link_hash}"})


async def react_to_message(
    client: MaxClient, group_id: int, message_id: int, reaction: str
) -> Dict[str, Any]:
    await client.invoke_method(
        opcode=178,
        payload={
            "chatId": group_id,
            "messageId": str(message_id),
            "reaction": {"reactionType": "EMOJI", "id": reaction},
        },
    )
    return await client.invoke_method(
        opcode=181,
        payload={"chatId": group_id, "messageId": str(message_id), "count": 100},
    )
