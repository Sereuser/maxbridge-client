import asyncio
import itertools
import json
import logging
import uuid
from typing import Any ,Callable ,Optional

import aiohttp
import websockets
from websockets .asyncio .client import ClientConnection

from functools import wraps

from .exceptions import APIError ,ConnectionError
from . import models

WS_HOST ="wss://ws-api.oneme.ru/websocket"
RPC_VERSION =11
# Match current MAX web client fingerprint from captured traffic
APP_VERSION ="26.3.6"
USER_AGENT ="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"

_logger =logging .getLogger (__name__ )


def ensure_connected (method :Callable ):
    @wraps (method )
    def wrapper (self ,*args ,**kwargs ):
        if self ._connection is None :
            raise RuntimeError ("WebSocket not connected. Call .connect() first.")
        return method (self ,*args ,**kwargs )

    return wrapper


class MaxClient :
    def __init__ (self ):
        self ._connection :Optional [ClientConnection ]=None
        self ._http_pool :Optional [aiohttp .ClientSession ]=None
        self ._is_logged_in :bool =False
        self ._device_id :Optional [str ]=None
        self ._seq =itertools .count (1 )
        self ._keepalive_task :Optional [asyncio .Task ]=None
        self ._recv_task :Optional [asyncio .Task ]=None
        self ._incoming_event_callback =None
        self ._reconnect_callback =None
        self ._closed :bool =False
        self ._pending ={}
        self ._video_pending ={}
        self ._file_pending ={}

        self ._cached_chats :dict [int ,dict ]={}
        self ._cached_users :dict [int ,dict ]={}
        self ._profile :Optional [dict ]=None



    async def connect (self ):
        if self ._connection :
            raise Exception ("Already connected")

        self ._closed =False
        _logger .info (f'Connecting to {WS_HOST }...')
        self ._connection =await websockets .connect (
        WS_HOST ,
        origin =websockets .Origin ('https://web.max.ru'),
        user_agent_header =USER_AGENT
        )

        self ._recv_task =asyncio .create_task (self ._recv_loop ())
        _logger .info ('Connected. Receive task started.')
        return self ._connection

    @ensure_connected
    async def disconnect (self ):
        self ._closed =True
        await self ._stop_keepalive_task ()
        if self ._recv_task :
            self ._recv_task .cancel ()
        await self ._connection .close ()
        self ._connection =None
        if self ._http_pool :
            await self ._http_pool .close ()
            self ._http_pool =None

    @ensure_connected
    async def invoke_method (self ,opcode :int ,payload :dict [str ,Any ],retries :int =2 ):
        seq =next (self ._seq )

        request ={
        "ver":RPC_VERSION ,
        "cmd":0 ,
        "seq":seq ,
        "opcode":opcode ,
        "payload":payload
        }
        _logger .info (f'-> REQUEST: {request }')

        future =asyncio .get_running_loop ().create_future ()
        self ._pending [seq ]=future

        try :
            await self ._connection .send (
            json .dumps (request )
            )
        except websockets .exceptions .ConnectionClosed :
            _logger .warning ('got ws disconnect in invoke_method')
            if self ._reconnect_callback :
                _logger .info ('reconnecting')
                await self ._reconnect_callback ()
                if retries >0 :
                    _logger .info ('retrying invoke_method after reconnect')
                    await self .invoke_method (opcode ,payload ,retries -1 )
            return

        try :
            response =await future
        except asyncio .CancelledError :
            self ._pending .pop (seq ,None )
            raise
        _logger .info (f'<- RESPONSE: {response }')


        if "error" in response .get ("payload", {}):
            payload = response.get("payload", {})
            error = payload.get("error")
            # Some responses return a string error instead of an object
            if isinstance(error, dict):
                code = error.get("code", -1)
                message = error.get("message", payload.get("message", "Unknown error"))
            else:
                code = -1
                message = payload.get("message") or str(error)

            raise APIError(code, message)

        return response

    async def set_callback (self ,function ):
        import warnings
        warnings .warn ('switch to set_packet_callback',category =DeprecationWarning )
        self .set_packet_callback (function )

    def set_packet_callback (self ,function ):
        if not asyncio .iscoroutinefunction (function ):
            raise TypeError ('callback must be async')
        self ._incoming_event_callback =function

    def set_reconnect_callback (self ,function ):
        if not asyncio .iscoroutinefunction (function ):
            raise TypeError ('callback must be async')
        self ._reconnect_callback =function
    async def debug_invoke (self ,opcode :int ,payload :dict | None =None ,timeout :float =5.0 ):
        """Invoke an opcode for debugging.

        This helper wraps `invoke_method` and catches exceptions, returning a
        structured report instead of raising.
        """
        payload = payload or {}
        try :
            response =await asyncio .wait_for (self .invoke_method (opcode ,payload ),timeout )
            return {
            "opcode":opcode ,
            "payload":payload ,
            "response":response ,
            "error":None
            }
        except Exception as e :
            return {
            "opcode":opcode ,
            "payload":payload ,
            "response":None ,
            "error":repr (e )
            }

    async def discover_opcodes (self ,start :int =1 ,end :int =120 ,payloads :dict | None =None ,delay :float =0.1 ):
        """Probe a range of opcodes to see what the server returns.

        **Warning**: This may trigger rate limiting or disconnects.
        """
        payloads = payloads or {}
        results = {}
        for opcode in range (start ,end +1 ):
            payload = payloads .get (opcode ,{})
            results [opcode ]=await self .debug_invoke (opcode ,payload )
            await asyncio .sleep (delay )
        return results
    async def _recv_loop (self ):
        while not self ._closed :
            try :
                packet =await self ._connection .recv ()
                packet =json .loads (packet )

            except asyncio .CancelledError :
                _logger .info ('receiver cancelled')
                return

            except websockets .exceptions .ConnectionClosedError as err :
                _logger .warning ('got ws disconnect in receiver')
                if not self ._is_logged_in :
                    raise err
                if self ._reconnect_callback :
                    _logger .info ('reconnecting')
                    asyncio .create_task (self ._reconnect_callback ())
                return

            except websockets .exceptions .ConnectionClosedOK :
                _logger .info ('connection closed by server')
                return

            except json .JSONDecodeError :
                _logger .warning ('could not decode packet')
                continue

            seq =packet ["seq"]
            future =self ._pending .pop (seq ,None )
            if future :
                future .set_result (packet )
                continue

            if packet .get ("opcode")==136 :
                payload =packet .get ("payload",{})
                future =None

                if "videoId"in payload :
                    future =self ._video_pending .pop (payload ["videoId"],None )
                elif "fileId"in payload :
                    future =self ._file_pending .pop (payload ["fileId"],None )

                if future :
                    future .set_result (None )

            if self ._incoming_event_callback :
                asyncio .create_task (self ._incoming_event_callback (self ,packet ))



    @ensure_connected
    async def _send_keepalive_packet (self ):
        try :
            async with asyncio .timeout (15 ):
                await self .invoke_method (
                opcode =1 ,
                payload ={"interactive":True }
                )
        except asyncio .TimeoutError :
            _logger .warning ('keepalive ping timed out')
            if self ._reconnect_callback :
                _logger .info ('reconnecting')
                asyncio .create_task (self ._reconnect_callback ())

    @ensure_connected
    async def _keepalive_loop (self ):
        _logger .info (f'keepalive task started')
        try :
            while True :
                await self ._send_keepalive_packet ()
                await asyncio .sleep (30 )
        except asyncio .CancelledError :
            _logger .info ('keepalive task stopped')
            return

    @ensure_connected
    async def _start_keepalive_task (self ):
        if self ._keepalive_task :
            raise Exception ('Keepalive task already started')

        self ._keepalive_task =asyncio .create_task (self ._keepalive_loop ())
        return

    async def _stop_keepalive_task (self ):
        if not self ._keepalive_task :
            raise Exception ('Keepalive task is not running')

        self ._keepalive_task .cancel ()
        self ._keepalive_task =None
        return



    @ensure_connected
    async def _send_hello_packet (self ,device_id :Optional [str ]=None ):
        self ._device_id =device_id or f'{uuid .uuid4 ()}'
        return await self .invoke_method (
        opcode =6 ,
        payload ={
        "userAgent":{
        "deviceType":"WEB",
        "locale":"ru",
        "deviceLocale":"ru",
        "osVersion":"Linux",
        "deviceName":"Chrome",
        "headerUserAgent":USER_AGENT ,
        "appVersion":APP_VERSION ,
        "screen":"720x1280 1.0x",
        "timezone":"Asia/Yekaterinburg"
        },
        "deviceId":self ._device_id ,
        }
        )

    @ensure_connected
    async def send_code (self ,phone :str )->str :
        """:returns: Login token."""
        await self ._send_hello_packet ()
        start_auth_response =await self .invoke_method (
        opcode =17 ,
        payload ={
        "phone":phone ,
        "type":"START_AUTH",
        "language":"ru"
        }
        )
        return start_auth_response ["payload"]["token"]

    @ensure_connected
    async def sign_in (self ,sms_token :str ,sms_code :int ):
        """
        Auth token for further login is at ['payload']['tokenAttrs']['LOGIN']['token']
        :param login_token: Must be obtained via `send_code`.
        """
        verification_response =await self .invoke_method (
        opcode =18 ,
        payload ={
        "token":sms_token ,
        "verifyCode":str (sms_code ),
        "authTokenType":"CHECK_CODE"
        }
        )

        if "error"in verification_response ["payload"]:
            raise Exception (verification_response ["payload"]["error"])


        if "profile"in verification_response ["payload"]:
            self ._profile =verification_response ["payload"]["profile"]


        if "chats"in verification_response ["payload"]:
            for chat in verification_response ["payload"]["chats"]:
                self ._cached_chats [chat ["id"]]=chat


        if "chats"in verification_response ["payload"]:
            user_ids =set ()
            for chat in verification_response ["payload"]["chats"]:
                if "participants"in chat :
                    for uid in chat ["participants"].keys ():
                        user_ids .add (int (uid ))
            if user_ids :

                try :
                    users_response =await self .invoke_method (
                    opcode =32 ,
                    payload ={"contactIds":list (user_ids )}
                    )
                    if "payload"in users_response and "contacts"in users_response ["payload"]:
                        for user in users_response ["payload"]["contacts"]:
                            self ._cached_users [user ["id"]]=user
                except Exception as e :
                    _logger .warning (f'Failed to fetch users: {e }')

        try :
            phone =verification_response ["payload"]["profile"]["contact"]["phone"]
        except :
            phone ='[?]'
            _logger .warning ('Got no phone number in server response')
        _logger .info (f'Successfully logged in as {phone }')

        self ._is_logged_in =True
        await self ._start_keepalive_task ()

        return verification_response

    @ensure_connected
    async def login_by_token (self ,token :str ,device_id :Optional [str ]=None ):
        await self ._send_hello_packet (device_id )
        _logger .info ("using session")
        login_response =await self .invoke_method (
        opcode =19 ,
        payload ={
        "interactive":True ,
        "token":token ,
        "chatsCount":40 ,
        "chatsSync":0 ,
        "contactsSync":0 ,
        "presenceSync":-1 ,
        "draftsSync":0
        }
        )

        if "error"in login_response ["payload"]:
            raise Exception (login_response ["payload"]["error"])


        if "profile"in login_response ["payload"]:
            self ._profile =login_response ["payload"]["profile"]


        if "chats"in login_response ["payload"]:
            for chat in login_response ["payload"]["chats"]:
                self ._cached_chats [chat ["id"]]=chat


        if "chats"in login_response ["payload"]:
            user_ids =set ()
            for chat in login_response ["payload"]["chats"]:
                if "participants"in chat :
                    for uid in chat ["participants"].keys ():
                        user_ids .add (int (uid ))
            if user_ids :

                try :
                    users_response =await self .invoke_method (
                    opcode =32 ,
                    payload ={"contactIds":list (user_ids )}
                    )
                    if "payload"in users_response and "contacts"in users_response ["payload"]:
                        for user in users_response ["payload"]["contacts"]:
                            self ._cached_users [user ["id"]]=user
                except Exception as e :
                    _logger .warning (f'Failed to fetch users: {e }')

        try :
            phone =login_response ["payload"]["profile"]["contact"]["phone"]
        except :
            phone ='[?]'
            _logger .warning ('Got no phone number in server response')
        _logger .info (f'Successfully logged in as {phone }')

        self ._is_logged_in =True
        await self ._start_keepalive_task ()

        return login_response

    @property
    def device_id (self )->Optional [str ]:
        return self ._device_id

    @property
    def profile (self )->Optional [dict ]:
        return self ._profile

    def get_cached_chats (self )->dict [int ,dict ]:
        return self ._cached_chats

    def get_cached_users (self )->dict [int ,dict ]:
        return self ._cached_users

    def get_chats_structured (self )->dict [int ,models .Chat ]:
        """Return cached chats as `Chat` models."""
        return {cid :models .Chat .from_raw (data )for cid ,data in self ._cached_chats .items ()}

    def get_users_structured (self )->dict [int ,models .User ]:
        """Return cached users as `User` models."""
        return {uid :models .User .from_raw (data )for uid ,data in self ._cached_users .items ()}

    @ensure_connected
    async def get_chat_messages (self ,chat_id :int ,from_ts :Optional [int ]=None ,backward :int =30 ,forward :int =0 ,get_messages :bool =True ):
        """Get messages from chat using the same opcode/shape as web client.

        :param chat_id: Chat identifier.
        :param from_ts: Anchor timestamp (ms). If not provided, tries to use lastEventTime/lastMessage.time from cache.
        :param backward: How many messages to request before ``from_ts``.
        :param forward: How many messages to request after ``from_ts``.
        :param get_messages: Whether to include messages in the response (web uses ``true``).
        """
        if from_ts is None :
            cached =self ._cached_chats .get (chat_id )
            if cached :
                from_ts =cached .get ("lastEventTime")or cached .get ("lastMessage" ,{}).get ("time")
        if from_ts is None :
            # Fallback to zero – server will interpret according to its defaults
            from_ts =0

        return await self .invoke_method (
        opcode =49 ,
        payload ={
        "chatId":chat_id ,
        "from":from_ts ,
        "forward":forward ,
        "backward":backward ,
        "getMessages":get_messages
        }
        )

    @ensure_connected
    async def get_chat_messages_structured (self ,chat_id :int ,from_ts :Optional [int ]=None ,backward :int =30 ,forward :int =0 )->list [models .Message ]:
        """Wrapper over `get_chat_messages` that returns a list of `Message` models."""
        raw =await self .get_chat_messages (chat_id ,from_ts =from_ts ,backward =backward ,forward =forward ,get_messages =True )
        payload =raw .get ("payload", {})
        msgs =payload .get ("messages")or []
        if isinstance (msgs ,dict ):
            iterable =msgs .values ()
        else :
            iterable =msgs
        return [models .Message .from_raw (m ,chat_id =chat_id )for m in iterable ]

    async def __aenter__ (self ):
        await self .connect ()
        return self

    async def __aexit__ (self ,exc_type ,exc_val ,exc_tb ):
        await self .disconnect ()
