import asyncio

from maxbridge import MaxClient


async def main() -> None:
    async with MaxClient() as client:
        await client.login_by_token("your_token_here")
        stream = client.create_bridge_event_stream(include_self=False)
        async for event in stream:
            if event.message is None:
                continue
            payload = {
                "source": "max",
                "chat_id": event.message.chat_id,
                "message_id": event.message.message_id,
                "sender_id": event.message.sender_id,
                "text": event.message.text,
                "attachments": [attachment.kind for attachment in event.message.attachments],
            }
            print(payload)


if __name__ == "__main__":
    asyncio.run(main())
