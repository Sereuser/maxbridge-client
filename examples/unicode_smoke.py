import asyncio

from maxbridge import MaxClient


async def main() -> None:
    async with MaxClient() as client:
        await client.login_by_token("your_token_here")
        chats = client.get_chats_structured()
        giga = next((chat for chat in chats.values() if (chat.title or "").lower() == "gigachat"), None)
        if giga is None:
            raise RuntimeError("GigaChat chat not found")
        await client.send_message(giga.id, "Проверка Unicode MaxBridge. Сообщение отправлено без потери символов.")


if __name__ == "__main__":
    asyncio.run(main())
