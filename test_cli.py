
import asyncio
import logging
from pathlib import Path
from maxbridge import MaxClient
from maxbridge .exceptions import APIError ,ConnectionError

logging .basicConfig (level =logging .INFO ,format ='[%(asctime)s] %(message)s')

async def main ():
    try :
        async with MaxClient ()as client :

            try :
                token =Path ('login_token.txt').read_text ().strip ()
            except FileNotFoundError :
                logging .error ("Файл login_token.txt не найден!")
                return

            logging .info ("Логинимся...")
            await client .login_by_token (token )


            await asyncio .sleep (3 )

            print ("\n"+"="*40 )
            print ("🤖 ПОЛУЧЕНИЕ ЧАТОВ ЧЕРЕЗ КЛИЕНТ")
            print ("="*40 )

            chats =client .get_cached_chats ()
            users =client .get_cached_users ()

            print (f"Тип полученных данных: {type (chats )}")
            print (f"Количество чатов: {len (chats )}")
            print (f"Количество пользователей: {len (users )}")

            for cid ,info in chats .items ():
                title ="Без названия"
                if info .get ('type')=='DIALOG':

                    participants =info .get ('participants',{})
                    owner =info .get ('owner')
                    for uid in participants :
                        if int (uid )!=owner :
                            user =users .get (int (uid ))
                            if user and 'names'in user :
                                name =user ['names'][0 ]['name']if user ['names']else str (uid )
                                title =name
                                break
                else :
                    title =info .get ('title','Без названия')

                print (f" -> ID: {cid } | Тип: {info .get ('type')} | Название: {title }")

            print ("="*40 )


            while True :
                print ("\n"+"="*50 )
                print ("МЕНЮ ВЗАИМОДЕЙСТВИЯ С ЧАТАМИ")
                print ("="*50 )
                print ("1. Просмотреть сообщения чата")
                print ("2. Отправить сообщение")
                print ("3. Выбрать другой чат")
                print ("4. Выход")
                print ("="*50 )

                try :
                    choice =input ("Выберите действие (1-4): ").strip ()

                    if choice =="1":

                        chat_id_input =input ("Введите ID чата: ").strip ()
                        try :
                            chat_id =int (chat_id_input )
                            messages =await client .get_chat_messages (chat_id ,count =20 )
                            print (f"\nСообщения чата {chat_id }:")
                            if "payload"in messages and "messages"in messages ["payload"]:
                                msgs =messages ["payload"]["messages"]
                                if msgs :
                                    for msg_id ,msg in msgs .items ():
                                        sender =msg .get ("sender","Unknown")
                                        text =msg .get ("text","")
                                        time_str =msg .get ("time",0 )
                                        print (f"[{time_str }] {sender }: {text }")
                                else :
                                    print ("Сообщений нет")
                            else :
                                print ("Не удалось получить сообщения")
                        except ValueError :
                            print ("Неверный ID чата")
                        except Exception as e :
                            print (f"Ошибка: {e }")

                    elif choice =="2":

                        chat_id_input =input ("Введите ID чата: ").strip ()
                        message_text =input ("Введите сообщение: ").strip ()
                        if message_text :
                            try :
                                chat_id =int (chat_id_input )
                                from maxbridge .functions import messages
                                response =await messages .send_message (client ,chat_id ,message_text )
                                print ("Сообщение отправлено!")
                            except ValueError :
                                print ("Неверный ID чата")
                            except Exception as e :
                                print (f"Ошибка: {e }")
                        else :
                            print ("Сообщение не может быть пустым")

                    elif choice =="3":

                        break

                    elif choice =="4":

                        return

                    else :
                        print ("Неверный выбор")

                except KeyboardInterrupt :
                    print ("\nВыход...")
                    return

                input ("\nНажмите Enter для продолжения...")
    except (APIError ,ConnectionError )as e :
        logging .error (f"Ошибка API: {e }")
    except Exception as e :
        logging .error (f"Неожиданная ошибка: {e }")




if __name__ =="__main__":
    try :
        asyncio .run (main ())
    except KeyboardInterrupt :
        pass