"""
Пример базового использования VK Max Client
"""
import asyncio
from maxbridge import MaxClient
from maxbridge .functions import messages

async def main ():
    async with MaxClient ()as client :

        token ="your_token_here"
        await client .login_by_token (token )


        chats =client .get_cached_chats ()
        print (f"Найдено чатов: {len (chats )}")


        for chat_id ,chat_info in chats .items ():
            chat_type =chat_info .get ('type','UNKNOWN')
            if chat_type =='DIALOG':

                users =client .get_cached_users ()
                participants =chat_info .get ('participants',{})
                owner =chat_info .get ('owner')
                for uid in participants :
                    if int (uid )!=owner :
                        user =users .get (int (uid ))
                        if user and 'names'in user :
                            name =user ['names'][0 ]['name']
                            print (f"Диалог с {name } (ID: {chat_id })")
                            break
            else :
                title =chat_info .get ('title','Без названия')
                print (f"{chat_type }: {title } (ID: {chat_id })")


        if chats :
            first_chat_id =list (chats .keys ())[0 ]
            await messages .send_message (client ,first_chat_id ,"Привет из VK Max Client!")
            print ("Сообщение отправлено!")

if __name__ =="__main__":
    asyncio .run (main ())