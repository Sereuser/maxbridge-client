from typing import Any, Dict, List

from ..client import MaxClient


async def resolve_users(client: MaxClient, user_ids: List[int]) -> Dict[str, Any]:
    return await client.invoke_method(opcode=32, payload={"contactIds": user_ids})


async def add_to_contacts(client: MaxClient, user_id: int) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=34,
        payload={"contactId": user_id, "action": "ADD"},
    )


async def ban(client: MaxClient, user_id: int) -> Dict[str, Any]:
    return await client.invoke_method(
        opcode=34,
        payload={"contactId": user_id, "action": "BLOCK"},
    )
