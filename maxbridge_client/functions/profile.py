from typing import Any, Dict, Optional

from ..client import MaxClient


async def change_online_status_visibility(
    client: MaxClient, hidden: bool
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=22,
        payload={"settings": {"user": {"HIDDEN": hidden}}},
    )


async def set_is_findable_by_phone(
    client: MaxClient, findable: bool
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=22,
        payload={
            "settings": {
                "user": {"SEARCH_BY_PHONE": "ALL" if findable else "CONTACTS"}
            }
        },
    )


async def set_calls_privacy(
    client: MaxClient, can_be_called: bool
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=22,
        payload={
            "settings": {
                "user": {"INCOMING_CALL": "ALL" if can_be_called else "CONTACTS"}
            }
        },
    )


async def invite_privacy(client: MaxClient, invitable: bool) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=22,
        payload={
            "settings": {
                "user": {"CHATS_INVITE": "ALL" if invitable else "CONTACTS"}
            }
        },
    )


async def change_profile(
    client: MaxClient,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    bio: Optional[str] = None,
) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=16,
        payload={
            "firstName": first_name,
            "lastName": last_name,
            "description": bio,
        },
    )
