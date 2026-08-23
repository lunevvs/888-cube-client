# Процедурные алгоритмы

Каждый алгоритм находится в отдельном Python-файле. Имя для параметра `--algorithm` совпадает с именем файла без расширения:

```text
--algorithm water_surface → algorithms/water_surface.py
```

Модуль должен экспортировать объект `ALGORITHM`, реализующий интерфейс `AnimationAlgorithm` из `algorithms/base.py`:

```python
from algorithms.base import AnimationAlgorithm


class Example(AnimationAlgorithm):
    name = "example"
    description = "Описание эффекта"
    recommended_fps = 8.0
    priority = "normal"
    default_fps = 8.0
    default_cycles = 1
    clear_after = True
    option_descriptions = {}

    def generate_frames(self, options: dict[str, str]) -> list[bytes]:
        # Один конечный и желательно бесшовный цикл.
        return [bytes(64)]


ALGORITHM = Example()
```

Требования интерфейса:

- `name` совпадает с именем файла;
- `description` кратко описывает эффект;
- `recommended_fps` содержит рекомендуемую частоту воспроизведения;
- `priority` описывает приоритет: `ambient`, `low`, `normal`, `high`, `critical` или `status`;
- `default_fps` задаёт частоту без явного `--fps`;
- `default_cycles` задаёт число циклов, а `None` означает бесконечное воспроизведение;
- `clear_after` определяет, нужно ли отправлять пустой кадр после завершения;
- `option_descriptions` перечисляет допустимые параметры `--algorithm-option`;
- `generate_frames(options)` возвращает непустую последовательность;
- каждый элемент последовательности имеет тип `bytes` и размер ровно 64 байта;
- последовательность описывает один полный цикл, который `draw.py` может повторять.

Значения `default_fps` и `default_cycles` используются только при отсутствии переопределения в командной строке.

## Обычные эффекты

| Алгоритм | Эффект | FPS | Циклы |
| --- | --- | ---: | ---: |
| `water_surface` | Пересекающиеся синусоидальные волны | 4 | ∞ |
| `double_helix` | Двойная спираль с перемычками | 4 | ∞ |
| `tornado` | Вращающаяся расширяющаяся воронка | 4 | ∞ |
| `bouncing_ball` | Объёмный шар, отражающийся от стенок | 4 | ∞ |
| `falling_shapes` | Падающие контуры квадрата, креста и ромба | 4 | ∞ |

## Уведомления

| Алгоритм | Приоритет | Эффект | FPS | Циклы |
| --- | --- | --- | ---: | ---: |
| `notification_soft` | low | Центральный импульс и спокойная орбита | 4 | 1 |
| `notification_incoming` | normal | Входящая плоскость складывается в маркер | 6 | 2 |
| `notification_reminder` | low | Медленно дышащий каркас | 3 | 3 |
| `notification_success` | normal | Восходящая плоскость и подтверждение | 8 | 1 |
| `notification_error` | high | Схлопывание и двойной импульс X | 8 | 2 |
| `notification_warning` | high | Двойной импульс внешнего каркаса | 6 | 3 |
| `notification_urgent` | critical | Быстрое схлопывание и раскрытие граней | 10 | 3 |
| `notification_progress` | status | Заполнение объёма снизу вверх, последний кадр сохраняется | 8 | 1 |
| `notification_waiting` | status | След обходит внешний каркас | 8 | ∞ |
| `notification_incoming_call` | high | Двойные сферические волны | 8 | ∞ |
| `notification_background_complete` | normal | Схождение частиц и финальная волна | 8 | 1 |
| `notification_connection_lost` | high | Каркас рассыпается и падает | 7 | 2 |
| `notification_connection_restored` | normal | Частицы собираются в каркас | 7 | 1 |

После конечного количества циклов `draw.py` обычно отправляет пустой кадр. Алгоритм `notification_progress` задаёт `clear_after = False`, поэтому достигнутое заполнение остаётся на кубе. Бесконечные уведомления с `clear_after = True` очищают куб при остановке через `Ctrl+C`.

## Запуск и переопределение

Использовать встроенные настройки уведомления:

```bash
python3 draw.py --algorithm notification_warning
```

Переопределить скорость и число циклов:

```bash
python3 draw.py \
  --algorithm notification_warning \
  --fps 4 \
  --cycles 1
```

Сделать конечное уведомление бесконечным:

```bash
python3 draw.py --algorithm notification_success --loop
```

Показать прогресс заполнения:

```bash
python3 draw.py \
  --algorithm notification_progress \
  --algorithm-option progress=75
```

`progress` принимает число от 0 до 100; значение по умолчанию — 50. После заполнения постоянно светится часть до `progress - 10%`, а последние 10 процентных пунктов моргают. Например, при 75% диапазон 0–65% остаётся включённым, а 65–75% моргает. При 100% внутренний объём 6×6×6 остаётся включённым, а внешняя оболочка куба моргает целиком. Финальный кадр всегда показывает полное значение и остаётся на кубе.
