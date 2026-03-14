"""
Пример простого эхо-бота для VK Max
"""
import asyncio
from maxbridge import MaxClient
from maxbridge .functions import messages

async def message_handler (client ,packet ):
    """Обработчик входящих сообщений"""
    if packet .get ("opcode")==64 :
        payload =packet .get ("payload",{})
        if "message"in payload :
            msg =payload ["message"]
            chat_id =payload .get ("chatId")
            text =msg .get ("text","")
            sender =msg .get ("sender")


            if sender !=client .profile .get ("contact",{}).get ("id"):

                response_text =f"Вы сказали: {text }"
                await messages .send_message (client ,chat_id ,response_text )
                print (f"Ответил на сообщение от {sender }: {text }")

async def main ():
    async with MaxClient ()as client :

        client .set_packet_callback (message_handler )


        token ="your_token_here"
        await client .login_by_token (token )

        print ("Бот запущен! Ожидание сообщений...")
        print ("Нажмите Ctrl+C для выхода")


        try :
            while True :
                await asyncio .sleep (1 )
        except KeyboardInterrupt :
            print ("Бот остановлен")

if __name__ =="__main__":
    asyncio .run (main ())