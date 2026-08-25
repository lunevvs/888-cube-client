# macOS Notification Subscriber

Небольшое фоновое AppleScript-приложение, которое читает видимые баннеры
`NotificationCenter` через Accessibility API и сохраняет их в файл
`notification` рядом с приложением.

После записи каждой JSON-строки приложение асинхронно запускает
`../handle_notification.py`, который выбирает команду `draw.py` по правилам из
`../config.yaml`. Запись в `notification` выполняется независимо от результата
обработчика.

Файл `notification` создаётся во время работы и исключён из Git.

Формат записи:

```json
{"datetime":"2026-08-25 13:09:59","appId":"com.apple.ScriptEditor2","appName":"Script Editor","notificationId":"DDC92BE1-9266-4243-86EB-A25A470FECDC","notificationDatetime":"1 минуту назад","notificationHeader":"Test","notificationBody":"Тестовое сообщение"}
```

Файл использует формат JSON Lines: каждая строка является отдельным JSON-объектом.
Если macOS не позволяет определить имя приложения, в `appName` записывается
bundle ID, а при отсутствии идентификатора — `unknown`.

`datetime` — время записи в журнал, а `notificationDatetime` — время, которое
показывает сама карточка (`1 минуту назад`, `вчера`, `13:45` и подобное). У
свежего баннера это значение может отсутствовать; тогда записывается пустая строка.

Журнал старого текстового формата после перехода на JSON сохранён в
`notification.legacy`.

Один баннер записывается только один раз, даже если он остаётся на экране
несколько циклов опроса. Одинаковые уведомления, показанные в разное время,
сохраняются как отдельные события. Уведомления, календарь, погода и другие
секции Notification Center записываются отдельными строками.

## Требования

- macOS;
- включённые баннеры уведомлений для приложения-отправителя;
- разрешение Accessibility для `subscribe-macos-notification.app`.

Перед первым запуском установите Python-зависимости из директории
`notification-subscriber`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Сборка

Перейдите в директорию подписчика из корня репозитория:

```bash
cd notification-subscriber/macos
```

Соберите stay-open приложение из исходника:

```bash
osacompile -s \
  -o subscribe-macos-notification.app \
  subscribe-macos-notification.applescript
```

Опция `-s` обязательна: она создаёт приложение, которое остаётся запущенным и
вызывает обработчик `idle` раз в секунду.

Проверить, что встроенный скрипт читается:

```bash
osadecompile \
  subscribe-macos-notification.app/Contents/Resources/Scripts/main.scpt
```

## Запуск

```bash
open subscribe-macos-notification.app
```

При первом запуске разрешите приложению управление `System Events`. Если macOS
не показала запрос или чтение уведомлений не работает, откройте:

```text
Системные настройки → Конфиденциальность и безопасность → Универсальный доступ
```

Добавьте туда `subscribe-macos-notification.app` и включите разрешение. После
изменения разрешения перезапустите приложение. После повторной сборки macOS
может считать приложение новым из-за изменившейся ad-hoc подписи. В таком случае
удалите старую запись из списка Accessibility, добавьте собранный `.app` заново
и снова включите разрешение.

Остановить подписчик:

```bash
osascript -e \
  'tell application "subscribe-macos-notification" to quit'
```

После повторной сборки уже запущенное приложение также нужно остановить и
запустить заново.

## Проверка

Очистка файла для проверки необязательна. Запомните его текущее число строк:

```bash
wc -l notification
```

Отправьте тестовое уведомление:

```bash
osascript -e \
  'display notification "Тестовое сообщение" with title "Test"'
```

Посмотрите журнал:

```bash
tail -f notification
```

Вывод и ошибки `handle_notification.py` и `draw.py` записываются отдельно:

```bash
tail -f ../handler.log
```

Ожидаемый результат — одна новая JSON-строка:

```json
{"datetime":"YYYY-MM-DD HH:MM:SS","appId":"com.apple.ScriptEditor2","appName":"Script Editor","notificationId":"UUID","notificationDatetime":"","notificationHeader":"Test","notificationBody":"Тестовое сообщение"}
```

Проверить последнюю строку с помощью `jq`:

```bash
tail -n 1 notification | jq .
```

Если вместо текста ничего не появляется, сначала убедитесь, что баннер реально
показывается на экране, затем повторно проверьте разрешение Accessibility.

## Автозапуск

Чтобы запускать подписчик после входа в систему, добавьте
`subscribe-macos-notification.app` в:

```text
Системные настройки → Основные → Объекты входа
```
