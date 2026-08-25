# Notification handler

`handle_notification.py` принимает один JSON-объект уведомления, применяет к
нему правила из `config.yaml` и запускает выбранную команду `draw.py`.

macOS-приложение из `macos/` вызывает обработчик автоматически после записи
каждого уведомления в `macos/notification`. Вызов выполняется асинхронно, а его
вывод и ошибки сохраняются в `handler.log`.

## Запуск

Один раз создайте локальное окружение и установите YAML-парсер:

```bash
cd notification-subscriber
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ..
```

Передать JSON как аргумент:

```bash
notification-subscriber/.venv/bin/python3 notification-subscriber/handle_notification.py \
  '{"datetime":"2026-08-25 13:40:02","appId":"com.apple.ScriptEditor2","appName":"Script Editor","notificationId":"UUID","notificationDatetime":"","notificationHeader":"Test","notificationBody":"Тестовое сообщение"}'
```

Передать последнюю строку журнала через stdin:

```bash
tail -n 1 notification-subscriber/macos/notification | \
  notification-subscriber/.venv/bin/python3 notification-subscriber/handle_notification.py -
```

Проверить выбранную команду без запуска `draw.py`:

```bash
tail -n 1 notification-subscriber/macos/notification | \
  notification-subscriber/.venv/bin/python3 notification-subscriber/handle_notification.py - --dry-run
```

Другой конфигурационный файл задаётся через `--config`:

```bash
notification-subscriber/.venv/bin/python3 notification-subscriber/handle_notification.py \
  --config /path/to/config.yaml \
  --dry-run \
  "$NOTIFICATION_JSON"
```

## Конфигурация

Правила в `rules` проверяются сверху вниз. Выполняется команда первого
совпавшего правила. Если совпадений нет, используется `defaultCommand`; если его
удалить, уведомление будет проигнорировано.

```yaml
drawScript: ../draw.py

rules:
  - name: errors-from-service
    filters:
      appId: com.example.service
      notificationHeader:
        regex: "(?i)(error|ошибка)"
      notificationBody:
        contains: database
    command:
      - --algorithm
      - notification_error
      - --cycles
      - "1"

defaultCommand:
  - --algorithm
  - notification_incoming
  - --cycles
  - "1"
```

Все фильтры одного правила объединяются логическим AND. Короткая строковая
запись означает точное совпадение:

```yaml
appId: com.example.service
```

Поддерживаемые операторы:

- `equals` — точное совпадение;
- `contains` — наличие подстроки;
- `regex` — регулярное выражение Python;
- `in` — значение входит в указанный массив строк.

Регулярное выражение не должно совпадать с пустой строкой. Например,
`(warn|внимание|)` содержит пустую альтернативу после последнего `|` и поэтому
ошибочно совпадает со всеми уведомлениями; обработчик отклонит такой конфиг.

В одном фильтре можно указать несколько операторов — они также применяются как
AND:

```yaml
notificationBody:
  contains: progress
  regex: "[0-9]+"
```

Аргументы команды поддерживают подстановку полей уведомления. Например:

```yaml
name: progress
filters:
  notificationHeader: Progress
command:
  - --algorithm
  - notification_progress
  - --algorithm-option
  - "progress={notificationBody}"
```

Команда передаётся процессу напрямую без shell. Поэтому данные уведомления не
могут превратиться в shell-команды; каждая строка массива остаётся одним
аргументом `draw.py`.

## Журнал обработчика

Посмотреть выбранные правила и вывод `draw.py`:

```bash
tail -f notification-subscriber/handler.log
```

Этот файл создаётся автоматически и исключён из Git. JSON-журнал уведомлений
остаётся в `macos/notification` независимо от результата запуска команды.
