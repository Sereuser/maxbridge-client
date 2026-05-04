# Справочник API MaxBridge

## Обзор

MaxBridge работает поверх WebSocket API MAX по адресу `wss://ws-api.oneme.ru/websocket`.
Запросы отправляются как JSON-объекты с полями `ver`, `cmd`, `seq`, `opcode`
и `payload`.

## Основной клиент

### `MaxClient`

Конструктор:

```python
MaxClient(
    ws_host: str = WS_HOST,
    locale: str = "ru",
    timezone: str = "Asia/Yekaterinburg",
    app_version: str = APP_VERSION,
    user_agent: str = USER_AGENT,
)
```

Основные методы:

- `connect()`
- `disconnect()`
- `login_by_token(token, device_id=None)`
- `start_with_token(token, device_id=None, reconnect_delay=5.0, auto_reconnect=True)`
- `run_forever(token, device_id=None, reconnect_delay=5.0)`
- `send_code(phone)`
- `sign_in(sms_token, sms_code)`
- `invoke_method(opcode, payload, retries=2)`
- `get_chat_messages(chat_id, from_ts=None, backward=30, forward=0, get_messages=True)`
- `get_chat_messages_structured(chat_id, from_ts=None, backward=30, forward=0)`
- `get_chat_messages_bridge(chat_id, from_ts=None, backward=30, forward=0)`
- `get_bridge_backfill_page(chat_id, from_ts=None, backward=30, forward=0)`
- `build_bridge_checkpoint(chat_id, message=None)`
- `send_message(chat_id, text, notify=True, reply_to=None, attaches=None)`
- `send_file(chat_id, file_path, caption="", notify=True)`
- `send_photo(chat_id, image_path, caption="", notify=True)`
- `resolve_users(user_ids)`
- `wait_until_connected(timeout=None)`
- `wait_until_logged_in(timeout=None)`
- `wait_until_stopped(timeout=None)`
- `to_bridge_message(raw_message, chat_id=None)`
- `to_bridge_event(packet)`
- `create_bridge_event_stream(include_self=True, include_non_message=False, allowed_kinds=None, max_queue_size=0)`

Методы доступа к кэшу:

- `get_cached_chats()`
- `get_cached_users()`
- `get_chats_structured()`
- `get_users_structured()`
- `profile`
- `device_id`

## Callback API

### Сырые пакеты

```python
async def handle_raw_packet(client, packet):
    ...


client.set_packet_callback(handle_raw_packet)
```

### Нормализованные пакеты

```python
from maxbridge.parser import PacketEnvelope


async def handle_packet(client, packet: PacketEnvelope):
    ...


client.set_parsed_packet_callback(handle_packet)
```

### Только сообщения

```python
async def handle_message(client, message):
    ...


client.set_message_callback(handle_message)
```

### State listeners

```python
async def on_state(client, state):
    print(state)


client.add_state_listener(on_state)
```

Состояния, которые сейчас эмитит библиотека:

- `connected`
- `logged_in`
- `disconnected`
- `reconnecting`
- `reconnected`

### Reconnect callback

```python
async def reconnect(client):
    await client.connect()
    await client.login_by_token("your_token")


client.set_reconnect_callback(reconnect)
```

## Парсер пакетов

### `PacketEnvelope`

- `ver`
- `cmd`
- `opcode`
- `seq`
- `payload`
- `raw`
- `message_event`
- `upload_event`

### `MessageEvent`

- `chat_id`
- `message`
- `raw`

### `UploadEvent`

- `file_id`
- `video_id`
- `raw`

## Bridge API

### `BridgeSender`

- `user_id`
- `display_name`
- `username`
- `avatar_url`
- `raw`

### `BridgeChat`

- `chat_id`
- `chat_type`
- `title`
- `peer_user_id`
- `raw`

### `BridgeAttachment`

- `kind`
- `attachment_id`
- `token`
- `url`
- `mime_type`
- `name`
- `raw`

### `BridgeMessage`

- `message_id`
- `event_id`
- `dedupe_key`
- `chat_id`
- `sender_id`
- `sender`
- `chat`
- `content`
- `text`
- `timestamp`
- `reply_to_message_id`
- `attachments`
- `raw`
- `is_empty`
- `normalized_text`

### `BridgeContent`

- `kind`
- `text`
- `options`
- `reaction_info`
- `metadata`
- `has_options`
- `is_textual`

### `BridgeEvent`

- `kind`
- `event_id`
- `dedupe_key`
- `opcode`
- `seq`
- `chat_id`
- `message`
- `upload`
- `raw`

### `BridgeEventStream`

Async iterator по нормализованным входящим событиям MAX. Подходит для bridge
приложений, которым нужен стабильный слой поверх сырого протокола.

### `BridgeEventLedger`

- `max_size`
- `seen_event_ids`
- `seen_dedupe_keys`

Методы:

- `register(event)`
- `contains(event)`
- `reset()`

### `BridgeRoomMapping`

- `max_chat_id`
- `matrix_room_id`
- `bridge_kind`
- `last_event_id`
- `last_dedupe_key`
- `raw`

### `BridgeRoomRegistry`

- `mappings`

Методы:

- `bind(mapping)`
- `resolve(max_chat_id)`
- `unbind(max_chat_id)`
- `values()`

### `BridgeCheckpoint`

- `chat_id`
- `last_message_id`
- `last_event_id`
- `last_dedupe_key`
- `last_timestamp`

### `BridgeBackfillPage`

- `chat_id`
- `messages`
- `checkpoint`
- `has_messages`

## Вспомогательные конструкторы

- `build_bridge_sender(raw_user)`
- `build_bridge_chat(raw_chat, current_user_id=None)`
- `build_bridge_attachment(raw)`
- `build_bridge_message(raw_message, chat_id=None, sender=None, chat=None)`
- `build_bridge_event(packet, sender=None, chat=None)`
- `make_event_id(chat_id, message_id)`
- `make_message_dedupe_key(chat_id, sender_id, timestamp, message_id)`
- `make_packet_event_id(opcode, seq)`
- `make_upload_event_id(file_id, video_id, seq)`
- `checkpoint_from_message(chat_id, message)`
- `advance_checkpoint(checkpoint, messages, chat_id)`
- `build_backfill_page(chat_id, messages)`

## Модели

### `User`

- `id: int`
- `name: str`
- `username: Optional[str]`
- `avatar: Optional[str]`

### `Chat`

- `id: int`
- `title: str`
- `type: str`
- `participants_count: Optional[int]`
- `avatar: Optional[str]`

### `Message`

- `id: str`
- `chat_id: int`
- `user_id: int`
- `text: str`
- `timestamp: int`
- `attaches: list[dict]`

## Модули функций

### `maxbridge.functions.messages`

- `send_message`
- `edit_message`
- `delete_message`
- `pin_message`
- `reply_message`
- `send_photo`
- `send_file`

### `maxbridge.functions.uploads`

- `upload_photo`
- `upload_video`
- `upload_file`
- `download_video`
- `download_file`

### `maxbridge.functions.users`

- `resolve_users`
- `add_to_contacts`
- `ban`

### `maxbridge.functions.channels`

- `resolve_channel_username`
- `resolve_channel_id`
- `join_channel`
- `create_channel`
- `mute_channel`

### `maxbridge.functions.groups`

- `create_group`
- `invite_users`
- `remove_users`
- `add_admin`
- `remove_admin`
- `transfer_group_ownership`
- `change_group_settings`
- `change_group_profile`
- `get_group_members`
- `resolve_group_by_link`
- `join_group_by_link`
- `react_to_message`

### `maxbridge.functions.profile`

- `change_online_status_visibility`
- `set_is_findable_by_phone`
- `set_calls_privacy`
- `invite_privacy`
- `change_profile`

## Известные opcodes

| Opcode | Назначение |
| --- | --- |
| `1` | Keepalive |
| `6` | Handshake hello |
| `17` | Запрос SMS-кода |
| `18` | Проверка SMS-кода |
| `19` | Авторизация по токену |
| `22` | Настройки пользователя/чата |
| `32` | Разрешение пользователей |
| `34` | Управление контактами |
| `48` | Информация о чате по id |
| `49` | История сообщений |
| `55` | Действия с чатом |
| `57` | Вход по invite-link |
| `64` | Отправка сообщения |
| `66` | Удаление сообщения |
| `67` | Редактирование сообщения |
| `77` | Операции с участниками и админами |
| `80` | Запрос URL для фото |
| `82` | Запрос URL для видео |
| `83` | URL для скачивания видео |
| `87` | Запрос URL для файла |
| `88` | URL для скачивания файла |
| `89` | Разрешение invite-link или username |
| `136` | Событие завершения загрузки |
| `178` | Добавление реакции |
| `181` | Загрузка реакций |

## Ошибки

Библиотечные исключения:

- `MaxException`
- `ConnectionError`
- `AuthenticationError`
- `APIError`

Пример:

```python
from maxbridge.exceptions import APIError, ConnectionError

try:
    await client.login_by_token("token")
except APIError as error:
    print(error.error_code, error.message)
except ConnectionError as error:
    print(error)
```

## Практические замечания

- Используйте `async with MaxClient()` для гарантированной очистки ресурсов.
- Для долгоживущих процессов используйте `start_with_token(...)` или `run_forever(...)`.
- `BridgeEventStream` предназначен для реального времени, `get_bridge_backfill_page(...)` — для backfill.
- Протокол MAX остаётся reverse-engineered и может меняться вместе с веб-клиентом.
