import asyncio

from maxbridge import MaxClient


async def main() -> None:
    async with MaxClient() as client:
        await client.login_by_token("your_token_here")
        ledger = client.create_bridge_event_ledger()
        registry = client.create_bridge_room_registry()
        chats = client.get_chats_structured()
        for chat in chats.values():
            client.bind_bridge_room(registry, chat.id, f"!room:{chat.id}")
        stream = client.create_bridge_event_stream(ledger=ledger, include_self=False)
        async for event in stream:
            if event.message is None:
                continue
            mapping = registry.resolve(event.message.chat_id)
            print(event.event_id, mapping.matrix_room_id if mapping else None)


if __name__ == "__main__":
    asyncio.run(main())
