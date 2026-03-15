# MaxBridge

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Asyncio](https://img.shields.io/badge/Asyncio-Supported-green.svg)](https://docs.python.org/3/library/asyncio.html)

Асинхронная Python библиотека для взаимодействия с API мессенджера MAX через WebSocket соединение.

## Описание

MaxBridge предоставляет удобный интерфейс для работы с мессенджером MAX, позволяя отправлять и получать сообщения, управлять чатами, пользователями и файлами в асинхронном режиме.

## 🚀 Быстрый старт

```python
import asyncio
from maxbridge import MaxClient

async def main():
    async with MaxClient() as client:
        # Авторизация по токену
        await client.login_by_token("ваш_токен")

        # Получение списка чатов
        chats = client.get_cached_chats()
        print(f"Найдено чатов: {len(chats)}")

asyncio.run(main())
```

## 📦 Установка

```bash
# Установка из PyPI (предполагается, что пакет опубликован)
pip install maxbridge

# Или из исходников
git clone https://github.com/Sereuser/max-bridge.git
cd max-bridge
pip install -e .
```

## 🔐 Авторизация

### По токену

**Важно:** Для авторизации необходимо получить токен доступа из веб-версии MAX.

#### Как получить токен:

1. Откройте https://web.max.ru в браузере
2. Авторизуйтесь в вашем аккаунте
3. Откройте DevTools (F12) → Application → Local Storage → https://web.max.ru
4. Найдите ключ `token` и скопируйте его значение

```python
async with MaxClient() as client:
    await client.login_by_token("ваш_длинный_токен")
```

**Примечание:** Токен является конфиденциальной информацией. Храните его securely.

## 💬 Работа с чатами

### Получение списка чатов

```python
chats = client.get_cached_chats()
for chat_id, chat_info in chats.items():
    print(f"ID: {chat_id}, Тип: {chat_info['type']}, Название: {chat_info.get('title', 'Диалог')}")
```

### Получение сообщений чата

```python
messages = await client.get_chat_messages(chat_id=123456, count=50, offset=0)
if "payload" in messages and "messages" in messages["payload"]:
    for msg_id, msg in messages["payload"]["messages"].items():
        print(f"{msg['sender']}: {msg['text']}")
```

## 📨 Отправка сообщений

```python
from maxbridge.functions import messages

# Текстовое сообщение
await messages.send_message(client, chat_id=123456, text="Привет!")

# С фото
await messages.send_photo(client, chat_id=123456, image_path="photo.jpg", caption="Фото")

# Реплай
await messages.reply_message(client, chat_id=123456, text="Ответ", reply_to_message_id="msg_id")
```

## 👥 Управление пользователями

```python
from maxbridge.functions import users

# Информация о пользователях
user_info = await users.resolve_users(client, user_ids=[12345, 67890])

# Добавить в контакты
await users.add_to_contacts(client, user_id=12345)
```

## 📁 Работа с файлами

```python
from maxbridge.functions import messages, uploads

# Отправка файла
await messages.send_file(client, chat_id=123456, file_path="document.pdf", caption="Документ")

# Скачивание файла
download_url = await uploads.download_file(
    client, chat_id=123456, message_id="msg_id", file_id=789
)
```

## 📺 Работа с медиа

```python
# Скачивание видео
video_url = await uploads.download_video(
    client, chat_id=123456, message_id="msg_id", video_id=101112
)
```

## 👥 Группы и каналы

```python
from maxbridge.functions import groups, channels

# Создание группы
await groups.create_group(client, "Название группы", participant_ids=[123, 456])

# Присоединение к каналу
await channels.join_channel(client, "username_канала")

# Информация о канале
channel_info = await channels.resolve_channel_username(client, "username")
```

## 🛠️ Обработка ошибок

```python
from maxbridge.exceptions import APIError, ConnectionError

try:
    await client.login_by_token("токен")
except APIError as e:
    print(f"Ошибка API {e.error_code}: {e.message}")
except ConnectionError:
    print("Ошибка подключения")
```

## 📊 Модели данных

```python
from maxbridge.models import User, Chat, Message

# Примеры
user = User(id=123, name="Имя", username="username")
chat = Chat(id=456, title="Название", type="DIALOG")
message = Message(id="msg_id", chat_id=456, user_id=123, text="Текст")
```

## 🔧 Продвинутые возможности

### Обработка событий в реальном времени

```python
def event_handler(client, packet):
    if packet.get("opcode") == 64:  # Новое сообщение
        print("Новое сообщение!")

client.set_packet_callback(event_handler)
```

### Кастомные настройки

```python
# Профиль
profile = client.profile

# Кэшированные пользователи
users = client.get_cached_users()
```

## 📚 Документация

- [API Reference](docs/API.md)
- [Примеры](examples/)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## 🏗️ Структура проекта

```
maxbridge/
├── __init__.py
├── client.py          # WebSocket клиент
├── models.py          # Модели данных
├── exceptions.py      # Исключения
├── packet.py          # Обработка пакетов
└── functions/         # API функции
    ├── __init__.py
    ├── messages.py    # Сообщения
    ├── users.py       # Пользователи
    ├── groups.py      # Группы
    ├── channels.py    # Каналы
    ├── profile.py     # Профиль
    └── uploads.py     # Загрузки

docs/                  # Документация
examples/              # Примеры
```

## ⚠️ Важные замечания

- Все методы асинхронные — используйте `await`
- Рекомендуется `async with MaxClient() as client:`
- Токены имеют срок действия
- Соблюдайте лимиты API

## 🐛 Отладка

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 📄 Лицензия

MIT License