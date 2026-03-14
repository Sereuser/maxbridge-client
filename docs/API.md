# VK Max API Documentation

## Обзор

VK Max Client предоставляет полный доступ к API мессенджера MAX через WebSocket соединение. Библиотека поддерживает все основные функции: отправка сообщений, управление чатами, загрузка файлов и многое другое.

## Архитектура

### WebSocket соединение

Библиотека использует постоянное WebSocket соединение к `wss://ws-api.oneme.ru/websocket` для обмена данными с серверами MAX.

### RPC протокол

Все запросы к API отправляются в формате JSON-RPC 2.0 с дополнительными полями:

```json
{
  "ver": 11,
  "cmd": 0,
  "seq": 123,
  "opcode": 64,
  "payload": {
    // Данные запроса
  }
}
```

- `ver`: Версия протокола (всегда 11)
- `cmd`: Тип команды (0 - запрос, 1 - ответ)
- `seq`: Порядковый номер запроса
- `opcode`: Код операции
- `payload`: Полезная нагрузка

## Авторизация

### Токен авторизации

Токены получаются через мобильное приложение MAX и имеют ограниченный срок действия.

```python
await client.login_by_token("длинный_токен_строка")
```

### SMS авторизация

```python
# Шаг 1: Запрос SMS
token = await client.send_code("+79991234567")

# Шаг 2: Ввод кода
await client.sign_in(token, 123456)
```

## Основные сущности

### Чаты (Chats)

Чаты бывают нескольких типов:
- `DIALOG`: Личный диалог
- `CHAT`: Групповой чат
- `CHANNEL`: Канал

Структура чата:
```python
{
  "id": 123456,
  "type": "DIALOG",
  "owner": 789,  # ID владельца
  "participants": {
    "789": 1640995200000,  # user_id: timestamp_присоединения
    "101": 1640995300000
  },
  "lastMessage": {
    "id": "msg_123",
    "sender": 789,
    "text": "Привет!",
    "time": 1640995400000
  }
}
```

### Сообщения (Messages)

```python
{
  "id": "msg_123",
  "sender": 789,
  "text": "Привет мир!",
  "time": 1640995400000,
  "type": "USER",
  "attaches": [],  # Вложения
  "elements": []   # Форматирование текста
}
```

### Пользователи (Users)

```python
{
  "id": 789,
  "names": [{"name": "Имя Фамилия", "firstName": "Имя", "lastName": "Фамилия"}],
  "options": ["TT", "ONEME"],  # Флаги пользователя
  "photoId": 12345,
  "baseUrl": "https://i.oneme.ru/i?r=..."
}
```

## API Methods

### Сообщения

#### send_message (opcode: 64)
Отправка текстового сообщения

**Параметры:**
- `chatId`: ID чата
- `message.text`: Текст сообщения
- `message.cid`: Client ID (генерируется автоматически)
- `notify`: Уведомлять участников (true/false)

**Пример:**
```python
await client.invoke_method(64, {
  "chatId": 123456,
  "message": {
    "text": "Привет!",
    "cid": 1640995400000,
    "elements": [],
    "attaches": []
  },
  "notify": True
})
```

#### edit_message (opcode: 67)
Редактирование сообщения

#### delete_message (opcode: 66)
Удаление сообщения

### Чаты и каналы

#### resolve_channel_id (opcode: 48)
Получение информации о чате/канале

**Параметры:**
- `chatIds`: Список ID чатов

### Пользователи

#### resolve_users (opcode: 32)
Получение информации о пользователях

**Параметры:**
- `contactIds`: Список ID пользователей

### Загрузка файлов

#### upload_photo/upload_file
Загрузка происходит в два этапа:
1. Получение URL для загрузки
2. HTTP POST загрузка файла
3. Отправка сообщения с вложением

## Обработка событий

### Входящие пакеты

Клиент автоматически обрабатывает входящие WebSocket пакеты. Для кастомной обработки установите callback:

```python
def my_handler(client, packet):
    if packet.get("opcode") == 64:  # Новое сообщение
        # Обработка нового сообщения
        pass

client.set_packet_callback(my_handler)
```

### Коды операций (Opcodes)

| Opcode | Описание |
|--------|----------|
| 1 | Keepalive |
| 6 | Hello packet |
| 17 | Запрос SMS кода |
| 18 | Проверка SMS кода |
| 19 | Авторизация по токену |
| 22 | Настройки пользователя |
| 32 | Информация о пользователях |
| 34 | Управление контактами |
| 48 | Информация о чате |
| 55 | Закрепление сообщения |
| 57 | Присоединение к каналу |
| 64 | Отправка сообщения |
| 66 | Удаление сообщения |
| 67 | Редактирование сообщения |
| 77 | Приглашение пользователей |
| 83 | Скачивание видео |
| 88 | Скачивание файла |
| 89 | Разрешение username канала |
| 136 | Статус загрузки файла |

## Ошибки

### Коды ошибок API

- `INVALID_TOKEN`: Недействительный токен
- `CHAT_NOT_FOUND`: Чат не найден
- `ACCESS_DENIED`: Доступ запрещен
- `RATE_LIMIT`: Превышен лимит запросов

### Обработка ошибок

```python
try:
    response = await client.invoke_method(opcode, payload)
except APIError as e:
    print(f"API Error {e.error_code}: {e.message}")
except ConnectionError:
    print("Connection lost")
```

## Лучшие практики

### 1. Управление соединением
```python
async with MaxClient() as client:
    # Соединение автоматически закроется
    await client.login_by_token(token)
```

### 2. Обработка отключений
```python
def reconnect_handler():
    asyncio.create_task(reconnect())

client.set_reconnect_callback(reconnect_handler)
```

### 3. Кэширование данных
```python
# Данные автоматически кэшируются после логина
chats = client.get_cached_chats()
users = client.get_cached_users()
```

### 4. Лимиты API
- Максимум 50 сообщений за запрос
- Ограничения на частоту отправки сообщений
- Лимиты на размер файлов

## Отладка

### Логирование
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Мониторинг соединения
```python
# Проверка статуса
print(f"Connected: {client._connection is not None}")
print(f"Logged in: {client._is_logged_in}")
```

## Расширение библиотеки

### Добавление новых функций

1. Изучите API через анализ трафика приложения
2. Определите opcode для новой функции
3. Создайте функцию в соответствующем модуле `functions/`
4. Добавьте типизацию и документацию

### Кастомные обработчики

```python
class MyMaxClient(MaxClient):
    async def on_message(self, message):
        # Кастомная обработка сообщений
        pass
```