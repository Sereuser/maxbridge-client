# Changelog

Все заметные изменения в проекте фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
а проект следует [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-05-04

### Добавлено
- Добавлен типизированный парсер пакетов с `PacketEnvelope`, `MessageEvent` и `UploadEvent`.
- Добавлены удобные helpers для отправки сообщений, файлов и фото.
- Добавлена совместимость импортов `from maxbridge import MaxClient`.
- Добавлен bridge-слой с `BridgeSender`, `BridgeChat`, `BridgeContent`, `BridgeMessage` и `BridgeEvent`.
- Добавлены persistent session primitives для долгоживущих WebSocket-расширений.
- Добавлены sync primitives: `BridgeCheckpoint`, `BridgeBackfillPage` и checkpoint-билдеры.
- Добавлены bridge-state primitives для дедупликации событий и mapping MAX chat -> Matrix room.

### Изменено
- Переписан жизненный цикл WebSocket-клиента, обработка callbacks и восстановление сессии.
- Нормализован публичный API для сообщений, профиля, каналов, групп и пользователей.
- Обновлены примеры, документация и упаковочные метаданные.
- Переведены README и API reference на русский язык.

### Исправлено
- Исправлены mutable defaults в message helpers.
- Исправлены payload-ошибки в группах и профиле.
- Исправлено несоответствие имён пакета между метаданными, примерами и импортами.
- Исправлено завершение upload futures.
- Исправлена сериализация Unicode в исходящих JSON payload.

## [0.2.5] - 2026-03-15

### Исправлено
- Устранён цикл импортов между `maxbridge_client.__init__` и `maxbridge_client.functions`.

## [0.2.0] - 2026-03-14

### Добавлено
- `get_chat_messages()` для чтения истории чата.
- Документация API в `docs/API.md`.
- Примеры использования в `examples/`.
- `CONTRIBUTING.md` и улучшение гидрации кэша после логина.

## [0.1.0] - 2026-03-14

### Добавлено
- Базовый WebSocket-клиент для MAX API.
- Авторизация по токену и через SMS.
- Отправка сообщений, работа с чатами, загрузка и скачивание файлов.
- Базовые модели данных и система исключений.
