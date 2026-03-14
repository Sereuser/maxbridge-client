# MaxBridge

Асинхронная Python библиотека для взаимодействия с API мессенджера MAX через WebSocket соединение.

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
# Клонируйте репозиторий
git clone <repository-url>
cd max-bridge

# Создайте виртуальное окружение
python -m venv venv
./venv/bin/pip install -r requirements.txt

# Или установите как пакет
pip install -e .
```

## 🔐 Авторизация

### По токену (единственный доступный метод)

**Важно:** Телефонная авторизация (по SMS) больше не поддерживается в MAX. Для авторизации необходимо получить токен доступа.

#### Как получить токен:

1. **Через веб-версию MAX:**
   - Откройте https://web.maximonline.ru в браузере
   - Авторизуйтесь в вашем аккаунте MAX
   - Откройте инструменты разработчика (F12)
   - Перейдите во вкладку "Application" → "Local Storage" → "https://web.maximonline.ru"
   - Найдите ключ `token` и скопируйте его значение

2. **Через мобильное приложение:**
   - Авторизуйтесь в приложении MAX
   - Используйте инструменты для извлечения токена из хранилища приложения

```python
async with MaxClient() as client:
    await client.login_by_token("ваш_длинный_токен")
```

**Примечание:** Токен является конфиденциальной информацией. Не храните его в открытом виде и не передавайте третьим лицам.

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

# Со вложениями
await messages.send_photo(client, chat_id=123456, image_path="photo.jpg", caption="Фото")

# Реплай на сообщение
await messages.reply_message(client, chat_id=123456, text="Ответ", reply_to_message_id="msg_id")
```

## 👥 Управление пользователями

### Получение информации о пользователях

```python
from maxbridge.functions import users

user_info = await users.resolve_users(client, user_ids=[12345, 67890])
```

### Добавление в контакты

```python
await users.add_to_contacts(client, user_id=12345)
```

## 📁 Работа с файлами

### Отправка файла

```python
from maxbridge.functions import messages

await messages.send_file(client, chat_id=123456, file_path="document.pdf", caption="Документ")
```

### Скачивание файла

```python
from maxbridge.functions import uploads

download_url = await uploads.download_file(
    client, chat_id=123456, message_id="msg_id", file_id=789
)
```

## 📺 Работа с медиа

### Скачивание видео

```python
video_url = await uploads.download_video(
    client, chat_id=123456, message_id="msg_id", video_id=101112
)
```

## 👥 Управление группами и каналами

```python
from maxbridge.functions import groups, channels

# Создание группы
await groups.create_group(client, "Название группы", participant_ids=[123, 456])

# Присоединение к каналу
await channels.join_channel(client, "username_канала")

# Получение информации о канале
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

# Пример структуры данных
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
# Получение профиля
profile = client.profile

# Получение списка пользователей
users = client.get_cached_users()
```

## � Документация

- [Полная документация API](docs/API.md) - подробное описание протокола и всех функций
- [Примеры использования](examples/) - готовые примеры кода- [Contributing Guide](CONTRIBUTING.md) - как внести вклад в проект
- [Changelog](CHANGELOG.md) - история изменений

## 🏗️ Структура проекта

```
vkmax/
├── client.py          # Основной WebSocket клиент
├── models.py          # Модели данных (User, Chat, Message)
├── exceptions.py      # Кастомные исключения
├── functions/         # API функции по категориям
│   ├── messages.py    # Отправка и управление сообщениями
│   ├── users.py       # Работа с пользователями
│   ├── groups.py      # Групповые чаты
│   ├── channels.py    # Каналы
│   └── uploads.py     # Загрузка файлов
└── __init__.py

docs/                  # Подробная документация
examples/              # Примеры использования
tests/                 # Тесты (планируется)
```

## 🔧 Установка для разработки

```bash
# Клонирование
git clone <repository-url>
cd max-bridge

# Создание виртуального окружения
python -m venv venv
./venv/bin/pip install -e .[dev]

# Форматирование кода
./venv/bin/black vkmax/ examples/

# Запуск тестов
./venv/bin/python test_cli.py
```
## ⚠️ Важные замечания

- Все методы асинхронные, используйте `await`
- Рекомендуется использовать контекстный менеджер `async with MaxClient() as client:`
- Токены авторизации имеют ограниченный срок действия
- Соблюдайте лимиты API для избежания блокировок

## 🐛 Отладка

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 📄 Лицензия

MIT License