# Contributing to VK Max Client

Спасибо за интерес к проекту! Вот как вы можете помочь развитию библиотеки.

## 🚀 Быстрый старт

1. Форкните репозиторий
2. Создайте ветку для вашей фичи: `git checkout -b feature/amazing-feature`
3. Установите зависимости: `./venv/bin/pip install -r requirements.txt`
4. Внесите изменения
5. Протестируйте: `./venv/bin/python test_cli.py`
6. Создайте коммит: `git commit -m 'Add amazing feature'`
7. Отправьте в ваш форк: `git push origin feature/amazing-feature`
8. Создайте Pull Request

## 📝 Стиль кода

### Python стиль
- Используйте `black` для форматирования
- Следуйте PEP 8
- Добавляйте типизацию (type hints)
- Документируйте функции docstrings

### Структура кода
```
vkmax/
├── client.py          # Основной клиент
├── models.py          # Модели данных
├── exceptions.py      # Исключения
├── functions/         # API функции
│   ├── __init__.py
│   ├── messages.py    # Функции сообщений
│   ├── users.py       # Функции пользователей
│   └── ...
└── __init__.py
```

## 🧪 Тестирование

### Запуск тестов
```bash
./venv/bin/python test_cli.py
```

### Добавление новых тестов
- Создавайте тесты в `tests/` директории
- Используйте `pytest` для запуска
- Тестируйте как успешные, так и ошибочные сценарии

## 🔍 Отладка API

### Анализ трафика
1. Используйте Wireshark или аналог для захвата WebSocket трафика
2. Анализируйте JSON пакеты
3. Определяйте opcode для новых функций

### Логирование
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Добавление новой функциональности

### 1. Исследование
- Изучите официальное приложение MAX
- Найдите нужную функцию в UI
- Захватите сетевой трафик

### 2. Реализация
```python
# functions/new_feature.py
async def new_function(client: MaxClient, param: str) -> dict:
    """Description of the function"""
    return await client.invoke_method(
        opcode=NEW_OPCODE,
        payload={"param": param}
    )
```

### 3. Документация
- Добавьте docstring
- Обновите `docs/API.md`
- Добавьте пример в `examples/`

### 4. Тестирование
- Протестируйте все сценарии
- Проверьте обработку ошибок
- Убедитесь в совместимости

## 🐛 Сообщение об ошибках

### Шаблон issue
```
**Описание проблемы:**
Краткое описание

**Шаги воспроизведения:**
1. Шаг 1
2. Шаг 2
3. Шаг 3

**Ожидаемое поведение:**
Что должно происходить

**Фактическое поведение:**
Что происходит на самом деле

**Скриншоты/логи:**
Приложите если возможно

**Среда:**
- OS: [Windows/Linux/Mac]
- Python: [версия]
- Версия библиотеки: [версия]
```

## 📋 Соглашение о коммитах

```
feat: add new message reactions
fix: handle connection timeout
docs: update API documentation
style: format code with black
refactor: simplify message parsing
test: add tests for file upload
```

## 🎯 Roadmap

### Краткосрочные цели
- [ ] Полная поддержка всех типов сообщений
- [ ] Поддержка групповых звонков
- [ ] Кэширование файлов
- [ ] Поддержка stickers

### Долгосрочные цели
- [ ] Синхронный API wrapper
- [ ] CLI инструмент
- [ ] GUI приложение
- [ ] Поддержка других платформ

## 📞 Контакты

- Issues: [GitHub Issues](https://github.com/username/max-bridge/issues)
- Discussions: [GitHub Discussions](https://github.com/username/max-bridge/discussions)

## 📄 Лицензия

Все контрибуции принимаются под лицензией MIT.