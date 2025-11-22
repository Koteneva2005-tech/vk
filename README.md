# Парсер расписания электричек (Туту)

`parse_sputnik.py` вытаскивает расписание электричек со страницы Туту (`https://www.tutu.ru/station.php?nnst=45807`) и превращает его в привычные структуры Python. Для каждого рейса берём время отправления, маршрут «Откуда -> Куда» и пометку дней хождения. Результаты фильтруются по дню (по умолчанию все) и сохраняются в JSON.

## Откуда берётся HTML

- В репозитории лежит заготовка `data/station_45807.html` (страница станции Москва Ярославская).
- При запуске с `--url` скрипт скачивает сайт и сохраняет его в `data/station_45807.html` (или в путь из `--save-html`, если указан).

```bash
python parse_sputnik.py --url https://www.tutu.ru/station.php?nnst=45807 --filter all
```

## Установка зависимостей

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

## Как запустить

- Все рейсы (по умолчанию читает `data/station_45807.html` и пишет `data/trips.json`):
  ```bash
  python parse_sputnik.py
  ```
- Только будни:
  ```bash
  python parse_sputnik.py --filter будни
  ```
- Только ежедневно + сохраняем в другой JSON:
  ```bash
  python parse_sputnik.py --filter ежедневно --json-out data/daily_trips.json
  ```
- Разобрать другой HTML (и указать путь для JSON):
  ```bash
  python parse_sputnik.py --html path/to/page.html --json-out path/to/trips.json
  ```

## Пример вывода (из сохранённого HTML)

```
Request date: 2025-11-21 12:00:00
04:10 Москва Ярославская -> Болшево (будни)
04:37 Москва Ярославская -> Мытищи (ежедневно)
```

В JSON сохраняется список словарей с полями `time`, `from`, `to`, `train_number`, `days`, `days_label`, `departure_iso`.

## Что сохраняется

- `data/trips.json` (или путь из `--json-out`) содержит объект `{ "requested_at": "...", "filter": "...", "trips": [...] }`.
- При скачивании по `--url` HTML обновляется и записывается в `data/station_45807.html` (можно переопределить `--save-html`).
