import asyncio

from maxbridge import MaxClient
from maxbridge.parser import PacketEnvelope


async def handle_packet(client: MaxClient, packet: PacketEnvelope) -> None:
    if packet.message_event is None:
        return
    profile = client.profile or {}
    current_user_id = profile.get("contact", {}).get("id")
    message = packet.message_event.message
    if message.user_id == current_user_id:
        return
    await client.send_message(message.chat_id, f"Echo: {message.text}")


async def main() -> None:
    async with MaxClient() as client:
        client.set_parsed_packet_callback(handle_packet)
        await client.login_by_token("your_token_here")
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
