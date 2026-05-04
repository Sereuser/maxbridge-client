import asyncio

from maxbridge import MaxClient


async def main() -> None:
    async with MaxClient() as client:
        await client.login_by_token("your_token_here")
        chats = client.get_chats_structured()
        print(f"Loaded chats: {len(chats)}")
        for chat_id, chat in chats.items():
            print(f"{chat_id}: {chat.type} {chat.title}")
        if chats:
            first_chat_id = next(iter(chats))
            await client.send_message(first_chat_id, "Hello from MaxBridge!")


if __name__ == "__main__":
    asyncio.run(main())
