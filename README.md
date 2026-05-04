# MaxBridge Client

Асинхронная Python-библиотека для работы с WebSocket API MAX.

## Возможности

- Авторизация по токену и через SMS
- Долгоживущая WebSocket-сессия с keepalive и автопереподключением
- Типизированные модели чатов, пользователей, сообщений и пакетов
- Нормализация событий для сценариев моста MAX <-> Matrix
- Нормализация контента сообщений, включая non-text payloads и варианты выбора
- Отправка сообщений, файлов, фото, чтение истории и работа с вложениями
- Примитивы backfill и checkpoint для сохранения и восстановления состояния

## Установка

```bash
pip install maxbridge-client
```

Для разработки:

```bash
git clone https://github.com/Sereuser/maxbridge-client.git
cd max-bridge
pip install -e .[dev]
```

## Импорт

Поддерживаются оба варианта импорта:

```python
from maxbridge import MaxClient
```

```python
from maxbridge_client import MaxClient
```

## Быстрый старт

```python
import asyncio

from maxbridge import MaxClient


async def main() -> None:
    async with MaxClient() as client:
        await client.login_by_token("your_token_here")
        chats = client.get_chats_structured()
        print(f"Чатов загружено: {len(chats)}")
        if chats:
            first_chat_id = next(iter(chats))
            await client.send_message(first_chat_id, "Привет из MaxBridge!")


asyncio.run(main())
```

## Авторизация

### По токену

```python
async with MaxClient() as client:
    await client.login_by_token("your_token_here")
```

### Через SMS

```python
async with MaxClient() as client:
    sms_token = await client.send_code("+79991234567")
    await client.sign_in(sms_token, 123456)
```

## Долгоживущая сессия

Для фоновых процессов и мостов удобнее использовать постоянное подключение:

```python
client = MaxClient()
await client.start_with_token("your_token_here", reconnect_delay=5.0)
await client.wait_until_logged_in()
```

Или запустить клиент в режиме daemon:

```python
await client.run_forever("your_token_here", reconnect_delay=5.0)
```

Если тестируете из PowerShell, лучше запускать код из файла `*.py`, а не через
подачу многострочного текста в stdin. Иначе кириллица может превратиться в `?`
ещё до того, как дойдёт до Python.

## События и парсинг пакетов

Сырой пакет:

```python
async def handle_raw_packet(client, packet):
    print(packet["opcode"])


client.set_packet_callback(handle_raw_packet)
```

Нормализованный пакет:

```python
from maxbridge.parser import PacketEnvelope


async def handle_packet(client, packet: PacketEnvelope):
    if packet.message_event is None:
        return
    message = packet.message_event.message
    await client.send_message(message.chat_id, f"Эхо: {message.text}")


client.set_parsed_packet_callback(handle_packet)
```

## Bridge API

Для сценариев моста используйте нормализованный слой:

```python
async with MaxClient() as client:
    await client.login_by_token("your_token_here")
    stream = client.create_bridge_event_stream(include_self=False)
    async for event in stream:
        if event.message is None:
            continue
        print(event.message.chat_id, event.message.sender_id, event.message.text)
```

История с checkpoint:

```python
page = await client.get_bridge_backfill_page(chat_id=123456, backward=50)
checkpoint = page.checkpoint
```

Стабильные идентификаторы события:

```python
message = page.messages[0]
print(message.event_id)
print(message.dedupe_key)
```

Состояние моста и дедупликация:

```python
ledger = client.create_bridge_event_ledger()
registry = client.create_bridge_room_registry()
mapping = client.bind_bridge_room(registry, max_chat_id=123456, matrix_room_id="!room:id")
```

Нормализация non-text сообщений:

```python
message = page.messages[0]
print(message.content.kind)
print(message.normalized_text)
if message.content.has_options:
    print(message.content.options)
```

## Основные операции

### Отправка текста

```python
await client.send_message(chat_id=123456, text="Привет")
```

### Ответ на сообщение

```python
from maxbridge.functions import messages


await messages.reply_message(
    client,
    chat_id=123456,
    text="Ответ",
    reply_to_message_id="message-id",
)
```

### Отправка файла

```python
await client.send_file(chat_id=123456, file_path="document.pdf", caption="Документ")
```

### Чтение истории

```python
history = await client.get_chat_messages_bridge(chat_id=123456, backward=50)
for message in history:
    print(message.sender_id, message.text)
```

### Разрешение пользователей

```python
users = await client.resolve_users([123, 456])
```

## Структура проекта

```text
maxbridge/
maxbridge_client/
  client.py
  bridge.py
  sync.py
  parser.py
  models.py
  exceptions.py
  functions/
docs/
examples/
tests/
```

## Документация

- [API reference](docs/API.md)
- [Примеры](examples/)
- [Пример bridge-цикла](examples/matrix_bridge_loop.py)
- [Пример bridge-state слоя](examples/bridge_state_demo.py)
- [Проверка Unicode через файл](examples/unicode_smoke.py)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Статус

Библиотека продолжает работать поверх reverse-engineered протокола MAX. При
изменении веб-клиента MAX возможны несовместимости, поэтому API специально
сделан с акцентом на проверяемые примитивы и устойчивые данные для моста.
