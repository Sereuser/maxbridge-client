import asyncio
import itertools
import json
import logging
import uuid
from functools import wraps
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, TypeVar, cast

import aiohttp
import websockets
from typing_extensions import Concatenate, ParamSpec
from websockets.asyncio.client import ClientConnection

from . import models
from .exceptions import APIError, ConnectionError
from .bridge import (
    BridgeEventLedger,
    BridgeChat,
    BridgeEvent,
    BridgeEventStream,
    BridgeMessage,
    BridgeSender,
    BridgeRoomMapping,
    BridgeRoomRegistry,
    build_bridge_chat,
    build_bridge_event,
    build_bridge_message,
    build_bridge_sender,
)
from .parser import PacketEnvelope, parse_packet
from .sync import BridgeBackfillPage, BridgeCheckpoint, build_backfill_page, checkpoint_from_message

if TYPE_CHECKING:
    from .bridge import BridgeMessage

WS_HOST = "wss://ws-api.oneme.ru/websocket"
RPC_VERSION = 11
APP_VERSION = "26.3.6"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)

PacketCallback = Callable[["MaxClient", Dict[str, Any]], Awaitable[None]]
ParsedPacketCallback = Callable[["MaxClient", PacketEnvelope], Awaitable[None]]
MessageCallback = Callable[["MaxClient", models.Message], Awaitable[None]]
ReconnectCallback = Callable[["MaxClient"], Awaitable[None]]
StateCallback = Callable[["MaxClient", str], Awaitable[None]]
P = ParamSpec("P")
R = TypeVar("R")

_logger = logging.getLogger(__name__)


def ensure_connected(
    method: Callable[Concatenate["MaxClient", P], R]
) -> Callable[Concatenate["MaxClient", P], R]:
    @wraps(method)
    def wrapper(self: "MaxClient", *args: P.args, **kwargs: P.kwargs) -> R:
        if self._connection is None:
            raise RuntimeError("WebSocket not connected. Call connect() first.")
        return method(self, *args, **kwargs)

    return wrapper


class MaxClient:
    def __init__(
        self,
        ws_host: str = WS_HOST,
        locale: str = "ru",
        timezone: str = "Asia/Yekaterinburg",
        app_version: str = APP_VERSION,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._ws_host = ws_host
        self._locale = locale
        self._timezone = timezone
        self._app_version = app_version
        self._user_agent = user_agent
        self._connection: Optional[ClientConnection] = None
        self._http_pool: Optional[aiohttp.ClientSession] = None
        self._is_logged_in = False
        self._device_id: Optional[str] = None
        self._seq = itertools.count(1)
        self._keepalive_task: Optional[asyncio.Task[None]] = None
        self._recv_task: Optional[asyncio.Task[None]] = None
        self._incoming_event_callback: Optional[PacketCallback] = None
        self._parsed_packet_callback: Optional[ParsedPacketCallback] = None
        self._message_callback: Optional[MessageCallback] = None
        self._packet_listeners: List[PacketCallback] = []
        self._parsed_packet_listeners: List[ParsedPacketCallback] = []
        self._message_listeners: List[MessageCallback] = []
        self._state_listeners: List[StateCallback] = []
        self._reconnect_callback: Optional[ReconnectCallback] = None
        self._closed = False
        self._session_token: Optional[str] = None
        self._session_device_id: Optional[str] = None
        self._auto_reconnect = False
        self._reconnect_delay = 5.0
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        self._pending: Dict[int, asyncio.Future[Dict[str, Any]]] = {}
        self._video_pending: Dict[int, asyncio.Future[Dict[str, Any]]] = {}
        self._file_pending: Dict[int, asyncio.Future[Dict[str, Any]]] = {}
        self._cached_chats: Dict[int, Dict[str, Any]] = {}
        self._cached_users: Dict[int, Dict[str, Any]] = {}
        self._profile: Optional[Dict[str, Any]] = None
        self._connected_event = asyncio.Event()
        self._logged_in_event = asyncio.Event()
        self._stopped_event = asyncio.Event()
        self._stopped_event.set()

    async def connect(self) -> ClientConnection:
        if self._connection is not None:
            raise ConnectionError("Client is already connected.")
        self._closed = False
        self._stopped_event.clear()
        _logger.info("Connecting to %s", self._ws_host)
        self._connection = await websockets.connect(
            self._ws_host,
            origin=websockets.Origin("https://web.max.ru"),
            user_agent_header=self._user_agent,
        )
        self._connected_event.set()
        self._recv_task = asyncio.create_task(self._recv_loop())
        await self._emit_state("connected")
        return self._connection

    @ensure_connected
    async def disconnect(self) -> None:
        self._closed = True
        self._auto_reconnect = False
        await self._stop_keepalive_task()
        await self._cancel_task(self._recv_task)
        self._recv_task = None
        await self._cancel_task(self._reconnect_task)
        self._reconnect_task = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
        await self._close_http_pool()
        self._connected_event.clear()
        self._logged_in_event.clear()
        self._reject_pending_futures("Client disconnected.")
        self._is_logged_in = False
        self._stopped_event.set()
        await self._emit_state("disconnected")

    @ensure_connected
    async def invoke_method(
        self, opcode: int, payload: Dict[str, Any], retries: int = 2
    ) -> Dict[str, Any]:
        seq = next(self._seq)
        request = {
            "ver": RPC_VERSION,
            "cmd": 0,
            "seq": seq,
            "opcode": opcode,
            "payload": payload,
        }
        future: asyncio.Future[Dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[seq] = future
        try:
            connection = self._connection
            if connection is None:
                raise ConnectionError("WebSocket connection is not available.")
            await connection.send(json.dumps(request, ensure_ascii=False))
        except websockets.exceptions.ConnectionClosed as connection_error:
            self._pending.pop(seq, None)
            await self._handle_connection_drop(connection_error, opcode, payload, retries)
            return await self.invoke_method(opcode, payload, retries=retries - 1)

        try:
            response = await future
        except asyncio.CancelledError:
            self._pending.pop(seq, None)
            raise

        api_error = self._extract_api_error(response)
        if api_error is not None:
            raise APIError(api_error["code"], api_error["message"])
        self._update_state_from_payload(response.get("payload") or {})
        return response

    async def set_callback(self, function: PacketCallback) -> None:
        import warnings

        warnings.warn(
            "set_callback() is deprecated, use set_packet_callback() instead.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        self.set_packet_callback(function)

    def set_packet_callback(self, function: PacketCallback) -> None:
        self._incoming_event_callback = function

    def add_packet_listener(self, function: PacketCallback) -> None:
        self._packet_listeners.append(function)

    def remove_packet_listener(self, function: PacketCallback) -> None:
        if function in self._packet_listeners:
            self._packet_listeners.remove(function)

    def set_parsed_packet_callback(self, function: ParsedPacketCallback) -> None:
        self._parsed_packet_callback = function

    def add_parsed_packet_listener(self, function: ParsedPacketCallback) -> None:
        self._parsed_packet_listeners.append(function)

    def remove_parsed_packet_listener(self, function: ParsedPacketCallback) -> None:
        if function in self._parsed_packet_listeners:
            self._parsed_packet_listeners.remove(function)

    def set_message_callback(self, function: MessageCallback) -> None:
        self._message_callback = function

    def add_message_listener(self, function: MessageCallback) -> None:
        self._message_listeners.append(function)

    def remove_message_listener(self, function: MessageCallback) -> None:
        if function in self._message_listeners:
            self._message_listeners.remove(function)

    def set_reconnect_callback(self, function: ReconnectCallback) -> None:
        self._reconnect_callback = function

    def add_state_listener(self, function: StateCallback) -> None:
        self._state_listeners.append(function)

    def remove_state_listener(self, function: StateCallback) -> None:
        if function in self._state_listeners:
            self._state_listeners.remove(function)

    async def wait_until_connected(self, timeout: Optional[float] = None) -> bool:
        return await self._wait_for_event(self._connected_event, timeout)

    async def wait_until_logged_in(self, timeout: Optional[float] = None) -> bool:
        return await self._wait_for_event(self._logged_in_event, timeout)

    async def wait_until_stopped(self, timeout: Optional[float] = None) -> bool:
        return await self._wait_for_event(self._stopped_event, timeout)

    async def start_with_token(
        self,
        token: str,
        device_id: Optional[str] = None,
        reconnect_delay: float = 5.0,
        auto_reconnect: bool = True,
    ) -> Dict[str, Any]:
        self._session_token = token
        self._session_device_id = device_id
        self._reconnect_delay = reconnect_delay
        self._auto_reconnect = auto_reconnect
        if self._connection is None:
            await self.connect()
        return await self.login_by_token(token, device_id=device_id)

    async def run_forever(
        self,
        token: str,
        device_id: Optional[str] = None,
        reconnect_delay: float = 5.0,
    ) -> None:
        await self.start_with_token(
            token,
            device_id=device_id,
            reconnect_delay=reconnect_delay,
            auto_reconnect=True,
        )
        await self.wait_until_stopped()

    def parse_packet(self, packet: Dict[str, Any]) -> PacketEnvelope:
        return parse_packet(packet)

    def resolve_bridge_sender(self, user_id: int) -> Optional[BridgeSender]:
        raw_user = self._cached_users.get(user_id)
        return build_bridge_sender(raw_user) if raw_user is not None else None

    def resolve_bridge_chat(self, chat_id: int) -> Optional[BridgeChat]:
        raw_chat = self._cached_chats.get(chat_id)
        current_user_id = (self._profile or {}).get("contact", {}).get("id")
        chat = build_bridge_chat(raw_chat, current_user_id=current_user_id)
        if (
            chat is not None
            and not chat.title
            and chat.peer_user_id is not None
        ):
            sender = self.resolve_bridge_sender(chat.peer_user_id)
            if sender is not None and sender.display_name:
                return BridgeChat(
                    chat_id=chat.chat_id,
                    chat_type=chat.chat_type,
                    title=sender.display_name,
                    peer_user_id=chat.peer_user_id,
                    raw=chat.raw,
                )
        return chat

    def to_bridge_message(
        self, raw_message: Dict[str, Any], chat_id: Optional[int] = None
    ) -> BridgeMessage:
        resolved_chat_id = chat_id if chat_id is not None else int(raw_message.get("chatId", 0))
        sender = self.resolve_bridge_sender(int(raw_message.get("sender", 0)))
        chat = self.resolve_bridge_chat(resolved_chat_id)
        return build_bridge_message(
            raw_message,
            chat_id=resolved_chat_id,
            sender=sender,
            chat=chat,
        )

    def to_bridge_event(self, packet: Dict[str, Any]) -> BridgeEvent:
        parsed = parse_packet(packet)
        sender = None
        chat = None
        if parsed.message_event is not None:
            sender = self.resolve_bridge_sender(parsed.message_event.message.user_id)
            chat = self.resolve_bridge_chat(parsed.message_event.chat_id)
        return build_bridge_event(packet, sender=sender, chat=chat)

    def create_bridge_event_stream(
        self,
        include_self: bool = True,
        include_non_message: bool = False,
        allowed_kinds: Optional[List[str]] = None,
        max_queue_size: int = 0,
        ledger: Optional[BridgeEventLedger] = None,
    ) -> BridgeEventStream:
        return BridgeEventStream(
            self,
            include_self=include_self,
            include_non_message=include_non_message,
            allowed_kinds=allowed_kinds,
            max_queue_size=max_queue_size,
            ledger=ledger,
        )

    def create_bridge_event_ledger(self, max_size: int = 10000) -> BridgeEventLedger:
        return BridgeEventLedger(max_size=max_size)

    def create_bridge_room_registry(self) -> BridgeRoomRegistry:
        return BridgeRoomRegistry()

    def bind_bridge_room(
        self,
        registry: BridgeRoomRegistry,
        max_chat_id: int,
        matrix_room_id: str,
        bridge_kind: str = "chat",
    ) -> BridgeRoomMapping:
        mapping = BridgeRoomMapping(
            max_chat_id=max_chat_id,
            matrix_room_id=matrix_room_id,
            bridge_kind=bridge_kind,
        )
        registry.bind(mapping)
        return mapping

    async def debug_invoke(
        self, opcode: int, payload: Optional[Dict[str, Any]] = None, timeout: float = 5.0
    ) -> Dict[str, Any]:
        payload = payload or {}
        try:
            response = await asyncio.wait_for(self.invoke_method(opcode, payload), timeout)
        except Exception as error:
            return {
                "opcode": opcode,
                "payload": payload,
                "response": None,
                "error": repr(error),
            }
        return {
            "opcode": opcode,
            "payload": payload,
            "response": response,
            "error": None,
        }

    async def discover_opcodes(
        self,
        start: int = 1,
        end: int = 120,
        payloads: Optional[Dict[int, Dict[str, Any]]] = None,
        delay: float = 0.1,
    ) -> Dict[int, Dict[str, Any]]:
        payloads = payloads or {}
        results: Dict[int, Dict[str, Any]] = {}
        for opcode in range(start, end + 1):
            results[opcode] = await self.debug_invoke(opcode, payloads.get(opcode, {}))
            await asyncio.sleep(delay)
        return results

    async def _recv_loop(self) -> None:
        while not self._closed and self._connection is not None:
            try:
                connection = self._connection
                if connection is None:
                    raise ConnectionError("WebSocket connection is not available.")
                packet_raw = await connection.recv()
                packet = cast(Dict[str, Any], json.loads(packet_raw))
            except asyncio.CancelledError:
                return
            except websockets.exceptions.ConnectionClosed as error:
                await self._mark_disconnected()
                await self._handle_connection_drop(error)
                return
            except json.JSONDecodeError:
                _logger.warning("Could not decode packet.")
                continue

            if self._resolve_pending_request(packet):
                continue

            if packet.get("opcode") == 136:
                self._resolve_upload_future(packet)

            self._update_state_from_payload(packet.get("payload") or {})
            await self._dispatch_packet(packet)

    @ensure_connected
    async def _send_keepalive_packet(self) -> None:
        try:
            await asyncio.wait_for(
                self.invoke_method(opcode=1, payload={"interactive": True}),
                timeout=15,
            )
        except asyncio.TimeoutError:
            _logger.warning("Keepalive ping timed out.")
            await self._trigger_reconnect()

    @ensure_connected
    async def _keepalive_loop(self) -> None:
        try:
            while True:
                await self._send_keepalive_packet()
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            return

    @ensure_connected
    async def _start_keepalive_task(self) -> None:
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def _stop_keepalive_task(self) -> None:
        await self._cancel_task(self._keepalive_task)
        self._keepalive_task = None

    @ensure_connected
    async def _send_hello_packet(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        self._device_id = device_id or str(uuid.uuid4())
        return await self.invoke_method(
            opcode=6,
            payload={
                "userAgent": {
                    "deviceType": "WEB",
                    "locale": self._locale,
                    "deviceLocale": self._locale,
                    "osVersion": "Linux",
                    "deviceName": "Chrome",
                    "headerUserAgent": self._user_agent,
                    "appVersion": self._app_version,
                    "screen": "720x1280 1.0x",
                    "timezone": self._timezone,
                },
                "deviceId": self._device_id,
            },
        )

    @ensure_connected
    async def send_code(self, phone: str) -> str:
        await self._send_hello_packet()
        response = await self.invoke_method(
            opcode=17,
            payload={"phone": phone, "type": "START_AUTH", "language": self._locale},
        )
        return str(response["payload"]["token"])

    @ensure_connected
    async def sign_in(self, sms_token: str, sms_code: int) -> Dict[str, Any]:
        response = await self.invoke_method(
            opcode=18,
            payload={
                "token": sms_token,
                "verifyCode": str(sms_code),
                "authTokenType": "CHECK_CODE",
            },
        )
        await self._fetch_contact_details()
        self._is_logged_in = True
        self._logged_in_event.set()
        await self._start_keepalive_task()
        await self._emit_state("logged_in")
        return response

    @ensure_connected
    async def login_by_token(
        self, token: str, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        self._session_token = token
        self._session_device_id = device_id
        await self._send_hello_packet(device_id)
        response = await self.invoke_method(
            opcode=19,
            payload={
                "interactive": True,
                "token": token,
                "chatsCount": 40,
                "chatsSync": 0,
                "contactsSync": 0,
                "presenceSync": -1,
                "draftsSync": 0,
            },
        )
        await self._fetch_contact_details()
        self._is_logged_in = True
        self._logged_in_event.set()
        await self._start_keepalive_task()
        await self._emit_state("logged_in")
        return response

    @property
    def device_id(self) -> Optional[str]:
        return self._device_id

    @property
    def profile(self) -> Optional[Dict[str, Any]]:
        return self._profile

    def get_cached_chats(self) -> Dict[int, Dict[str, Any]]:
        return dict(self._cached_chats)

    def get_cached_users(self) -> Dict[int, Dict[str, Any]]:
        return dict(self._cached_users)

    def get_chats_structured(self) -> Dict[int, models.Chat]:
        return {
            chat_id: self._build_chat_model(chat_id, data)
            for chat_id, data in self._cached_chats.items()
        }

    def get_users_structured(self) -> Dict[int, models.User]:
        return {
            user_id: models.User.from_raw(data)
            for user_id, data in self._cached_users.items()
        }

    @ensure_connected
    async def get_chat_messages(
        self,
        chat_id: int,
        from_ts: Optional[int] = None,
        backward: int = 30,
        forward: int = 0,
        get_messages: bool = True,
    ) -> Dict[str, Any]:
        anchor = self._resolve_chat_anchor(chat_id, from_ts)
        return await self.invoke_method(
            opcode=49,
            payload={
                "chatId": chat_id,
                "from": anchor,
                "forward": forward,
                "backward": backward,
                "getMessages": get_messages,
            },
        )

    @ensure_connected
    async def get_chat_messages_structured(
        self,
        chat_id: int,
        from_ts: Optional[int] = None,
        backward: int = 30,
        forward: int = 0,
    ) -> List[models.Message]:
        raw = await self.get_chat_messages(
            chat_id,
            from_ts=from_ts,
            backward=backward,
            forward=forward,
            get_messages=True,
        )
        payload = raw.get("payload", {})
        messages = payload.get("messages") or []
        iterable = messages.values() if isinstance(messages, dict) else messages
        return [models.Message.from_raw(item, chat_id=chat_id) for item in iterable]

    @ensure_connected
    async def get_chat_messages_bridge(
        self,
        chat_id: int,
        from_ts: Optional[int] = None,
        backward: int = 30,
        forward: int = 0,
    ) -> List[BridgeMessage]:
        raw = await self.get_chat_messages(
            chat_id,
            from_ts=from_ts,
            backward=backward,
            forward=forward,
            get_messages=True,
        )
        payload = raw.get("payload", {})
        messages = payload.get("messages") or []
        iterable = messages.values() if isinstance(messages, dict) else messages
        chat = self.resolve_bridge_chat(chat_id)
        return [
            build_bridge_message(
                item,
                chat_id=chat_id,
                sender=self.resolve_bridge_sender(int(item.get("sender", 0))),
                chat=chat,
            )
            for item in iterable
        ]

    @ensure_connected
    async def get_bridge_backfill_page(
        self,
        chat_id: int,
        from_ts: Optional[int] = None,
        backward: int = 30,
        forward: int = 0,
    ) -> BridgeBackfillPage:
        messages = await self.get_chat_messages_bridge(
            chat_id,
            from_ts=from_ts,
            backward=backward,
            forward=forward,
        )
        return build_backfill_page(chat_id, messages)

    def build_bridge_checkpoint(
        self, chat_id: int, message: Optional[BridgeMessage] = None
    ) -> Optional[BridgeCheckpoint]:
        if message is not None:
            return checkpoint_from_message(chat_id, message)
        cached = self._cached_chats.get(chat_id, {})
        raw_message = cached.get("lastMessage")
        if not isinstance(raw_message, dict):
            return None
        bridge_message = self.to_bridge_message(raw_message, chat_id=chat_id)
        return checkpoint_from_message(chat_id, bridge_message)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        notify: bool = True,
        reply_to: Optional[str] = None,
        attaches: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        from .functions import messages

        return await messages.send_message(
            self,
            chat_id=chat_id,
            text=text,
            notify=notify,
            reply_to=reply_to,
            attaches=attaches,
        )

    async def send_file(
        self, chat_id: int, file_path: str, caption: str = "", notify: bool = True
    ) -> Dict[str, Any]:
        from .functions import messages

        return await messages.send_file(
            self,
            chat_id=chat_id,
            file_path=file_path,
            caption=caption,
            notify=notify,
        )

    async def send_photo(
        self, chat_id: int, image_path: str, caption: str = "", notify: bool = True
    ) -> Dict[str, Any]:
        from .functions import messages

        return await messages.send_photo(
            self,
            chat_id=chat_id,
            image_path=image_path,
            caption=caption,
            notify=notify,
        )

    async def resolve_users(self, user_ids: List[int]) -> Dict[str, Any]:
        from .functions import users

        return await users.resolve_users(self, user_ids=user_ids)

    async def __aenter__(self) -> "MaxClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._connection is not None:
            await self.disconnect()

    async def _dispatch_packet(self, packet: Dict[str, Any]) -> None:
        parsed = parse_packet(packet)
        if self._incoming_event_callback is not None:
            await self._invoke_callback(self._incoming_event_callback, self, packet)
        for packet_listener in self._packet_listeners:
            await self._invoke_callback(packet_listener, self, packet)
        if self._parsed_packet_callback is not None:
            await self._invoke_callback(self._parsed_packet_callback, self, parsed)
        for parsed_listener in self._parsed_packet_listeners:
            await self._invoke_callback(parsed_listener, self, parsed)
        if parsed.message_event is not None and self._message_callback is not None:
            await self._invoke_callback(
                self._message_callback, self, parsed.message_event.message
            )
        if parsed.message_event is not None:
            for message_listener in self._message_listeners:
                await self._invoke_callback(
                    message_listener, self, parsed.message_event.message
                )

    async def _invoke_callback(self, callback: Callable[..., Any], *args: Any) -> None:
        result = callback(*args)
        if isawaitable(result):
            await result

    async def _handle_connection_drop(
        self,
        error: Exception,
        opcode: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        retries: int = 0,
    ) -> None:
        _logger.warning("Connection dropped: %s", error)
        if self._auto_reconnect and self._can_restore_session():
            await self._schedule_reconnect()
            if opcode is not None and payload is not None and retries > 0:
                restored = await self.wait_until_logged_in(
                    timeout=max(self._reconnect_delay * 3, 10.0)
                )
                if restored:
                    return
            if opcode is None:
                return
        if not self._is_logged_in or retries <= 0:
            self._stopped_event.set()
            raise ConnectionError(str(error)) from error
        await self._trigger_reconnect()
        if self._connection is None and opcode is not None and payload is not None:
            raise ConnectionError("Reconnect callback did not restore the connection.")

    async def _trigger_reconnect(self) -> None:
        if self._reconnect_callback is None:
            return
        await self._invoke_callback(self._reconnect_callback, self)

    async def _schedule_reconnect(self) -> None:
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        await self._emit_state("reconnecting")

    async def _reconnect_loop(self) -> None:
        while not self._closed and self._can_restore_session():
            try:
                await self._restore_session()
                await self._emit_state("reconnected")
                return
            except Exception as error:
                _logger.warning("Reconnect attempt failed: %s", error)
                await asyncio.sleep(self._reconnect_delay)
        self._stopped_event.set()

    async def _restore_session(self) -> None:
        if self._connection is not None:
            return
        await self.connect()
        token = self._session_token
        if token is None:
            raise ConnectionError("No stored token for reconnect.")
        await self.login_by_token(token, device_id=self._session_device_id)

    def _extract_api_error(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = response.get("payload") or {}
        error = payload.get("error")
        if error is None:
            return None
        if isinstance(error, dict):
            return {
                "code": int(error.get("code", -1)),
                "message": str(error.get("message", payload.get("message", "Unknown error"))),
            }
        return {"code": -1, "message": str(payload.get("message") or error)}

    def _resolve_pending_request(self, packet: Dict[str, Any]) -> bool:
        seq = packet.get("seq")
        if not isinstance(seq, int):
            return False
        future = self._pending.pop(seq, None)
        if future is None or future.done():
            return False
        future.set_result(packet)
        return True

    def _resolve_upload_future(self, packet: Dict[str, Any]) -> None:
        payload = packet.get("payload", {})
        future: Optional[asyncio.Future[Dict[str, Any]]] = None
        if "videoId" in payload:
            future = self._video_pending.pop(int(payload["videoId"]), None)
        elif "fileId" in payload:
            future = self._file_pending.pop(int(payload["fileId"]), None)
        if future is not None and not future.done():
            future.set_result(packet)

    def _resolve_chat_anchor(self, chat_id: int, from_ts: Optional[int]) -> int:
        if from_ts is not None:
            return from_ts
        cached = self._cached_chats.get(chat_id, {})
        return int(
            cached.get("lastEventTime")
            or cached.get("lastMessage", {}).get("time")
            or 0
        )

    def _update_state_from_payload(self, payload: Dict[str, Any]) -> None:
        profile = payload.get("profile")
        if isinstance(profile, dict):
            self._profile = profile
        chats = payload.get("chats")
        if isinstance(chats, list):
            for chat in chats:
                if isinstance(chat, dict) and "id" in chat:
                    self._cached_chats[int(chat["id"])] = chat
            self._hydrate_users_from_chats(chats)
        message = payload.get("message")
        chat_id = payload.get("chatId")
        if isinstance(chat_id, int) and isinstance(message, dict):
            cached_chat = self._cached_chats.setdefault(chat_id, {"id": chat_id})
            cached_chat["lastMessage"] = message
            if "time" in message:
                cached_chat["lastEventTime"] = message["time"]

    def _build_chat_model(self, chat_id: int, data: Dict[str, Any]) -> models.Chat:
        chat = models.Chat.from_raw(data)
        if chat.type != "DIALOG" or chat.title:
            return chat
        profile_id = (self._profile or {}).get("contact", {}).get("id")
        participants = data.get("participants") or {}
        for user_id in participants.keys():
            try:
                normalized = int(user_id)
            except (TypeError, ValueError):
                continue
            if profile_id is not None and normalized == profile_id:
                continue
            user = self._cached_users.get(normalized) or {}
            names = user.get("names") or []
            if names and names[0].get("name"):
                chat.title = str(names[0]["name"])
                return chat
        return chat

    def _hydrate_users_from_chats(self, chats: List[Dict[str, Any]]) -> None:
        for chat in chats:
            participants = chat.get("participants") or {}
            for user_id in participants.keys():
                try:
                    normalized = int(user_id)
                except (TypeError, ValueError):
                    continue
                self._cached_users.setdefault(normalized, {"id": normalized})

    async def _fetch_contact_details(self) -> None:
        user_ids = sorted(self._cached_users)
        if not user_ids:
            return
        try:
            response = await self.invoke_method(opcode=32, payload={"contactIds": user_ids})
        except APIError:
            raise
        except Exception as error:
            _logger.warning("Failed to hydrate user cache: %s", error)
            return
        contacts = response.get("payload", {}).get("contacts") or []
        for contact in contacts:
            if isinstance(contact, dict) and "id" in contact:
                self._cached_users[int(contact["id"])] = contact

    async def _cancel_task(self, task: Optional[asyncio.Task[Any]]) -> None:
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _close_http_pool(self) -> None:
        if self._http_pool is not None:
            await self._http_pool.close()
            self._http_pool = None

    async def _mark_disconnected(self) -> None:
        self._connection = None
        self._is_logged_in = False
        self._connected_event.clear()
        self._logged_in_event.clear()
        await self._stop_keepalive_task()
        await self._close_http_pool()
        self._reject_pending_futures("Connection dropped.")
        await self._emit_state("disconnected")

    def _reject_pending_futures(self, message: str) -> None:
        error = ConnectionError(message)
        for collection in (self._pending, self._video_pending, self._file_pending):
            for future in collection.values():
                if not future.done():
                    future.set_exception(error)
            collection.clear()

    async def _emit_state(self, state: str) -> None:
        for listener in self._state_listeners:
            await self._invoke_callback(listener, self, state)

    async def _wait_for_event(
        self, event: asyncio.Event, timeout: Optional[float]
    ) -> bool:
        try:
            if timeout is None:
                await event.wait()
            else:
                await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            return False
        return True

    def _can_restore_session(self) -> bool:
        return self._session_token is not None
