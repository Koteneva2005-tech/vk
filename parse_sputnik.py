import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup


DEFAULT_URL = "https://www.tutu.ru/station.php?nnst=45807"
# Базовый URL сервиса для выбранной станции.
DEFAULT_HTML_PATH = Path("data/station_45807.html")
# Путь для создания/чтения локальной копии HTML.
DEFAULT_JSON_PATH = Path("data/trips.json")
# Файл, куда по умолчанию сохраняется расписание в JSON.


def load_html(source_path: Path, url: Optional[str], save_html: Optional[Path]) -> str:
    """
    Load HTML either from the local filesystem or by downloading from the given URL.
    """
    if url:
# Если указан URL, скачиваем страницу и сохраняем её повседительно.
        response = requests.get(url)
        response.raise_for_status()
        html = response.text
        if save_html:
            save_html.parent.mkdir(parents=True, exist_ok=True)
            save_html.write_text(html, encoding="utf-8")
        return html

    path = source_path.expanduser()
# Если URL не указан, чтем письмо по указанному путю.
    if not path.exists():
        raise FileNotFoundError(
            f"Не найден файл {path}. Укажите --url для скачивания или путь к готовому HTML."
        )
# Возвращаем текст локального файла, когда он уже загружен.
    return path.read_text(encoding="utf-8")


def find_timetable(values: Dict) -> List[Dict]:
    """
    In the "__NEXT_DATA__" payload look for the node that contains the timetable array.
    The key is динамический, поэтому ищем первый словарь с полем "timetable".
    """
# Перебираем вложенные словари, пока не увидим нужную секцию timetable.
    for value in values.values():
        if isinstance(value, dict) and "timetable" in value:
            return value["timetable"]
# Если timetable нигде не обнаруется, выдаём понятное исключение.
    raise ValueError("Не удалось найти блок с расписанием в HTML.")


def classify_schedule_days(days: Iterable[int]) -> str:
    day_set = set(days)
# Все дни проходят по будням, возвращаем пометку «будние».
    if day_set == {1, 2, 3, 4, 5}:
        return "будни"
# Каждый день сети, значит поезд ходит ежедневно.
    if day_set == {1, 2, 3, 4, 5, 6, 7}:
        return "ежедневно"
# Остальные комбинации считаются частичными.


def parse_trips(html: str) -> List[Dict]:
    # Разбираем HTML и ищем встроенный скрипт с данными Next.js.
    soup = BeautifulSoup(html, "html.parser")
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag or not script_tag.string:
        raise ValueError("Скрипт с данными \"__NEXT_DATA__\" не найден.")

    data = json.loads(script_tag.string)
    # Берем payload со всеми данными страницы.
    values = data.get("props", {}).get("pageProps", {}).get("values", {})
    timetable = find_timetable(values)

    trips = []
    for item in timetable:
        dep_datetime = datetime.fromisoformat(item["departureDateTime"])
        route = item["train"]["route"]
        schedule_days = item.get("schedule", [])
        # Составляем запись рейса с временными метками, маршрутами и расписанием.
        trips.append(
            {
                "time": dep_datetime.strftime("%H:%M"),
                "departure_iso": dep_datetime.isoformat(),
                "from": route["departure"]["name"],
                "to": route["arrival"]["name"],
                "train_number": item["train"].get("number", ""),
                "days": schedule_days,
                "days_label": classify_schedule_days(schedule_days),
            }
        )

    # Сортируем записи по времени отправления перед возвратом списка.
    trips.sort(key=lambda trip: trip["departure_iso"])
    return trips


def filter_trips(trips: List[Dict], filter_mode: str) -> List[Dict]:
    # Если фильтр задан как «all» или русские аналогии, возвращаем все рейсы.
    if filter_mode in {"all", "все", "всё"}:
        return trips
    # В противном случае отбираем заявки по метке days_label.
    return [trip for trip in trips if trip["days_label"] == filter_mode]


def main() -> None:
    # Формируем аргументы командной строки для выбора HTML, URL и фильтра расписания.
    parser = argparse.ArgumentParser(
        description="Парсер расписания электричек Туту (станция 45807)."
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML_PATH,
        help=f"Путь к сохранённому HTML (по умолчанию {DEFAULT_HTML_PATH}).",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Если указать, HTML будет скачан с этого адреса (по умолчанию {DEFAULT_URL}). Чтобы использовать локальный файл, передайте пустую строку: --url \"\".",
    )
    parser.add_argument(
        "--save-html",
        type=Path,
        default=None,
        help="Куда сохранить скачанную страницу (если использован --url).",
    )
    parser.add_argument(
        "--filter",
        dest="filter_mode",
        choices=["будни", "ежедневно", "all", "все", "всё"],
        default="all",
        help="Отбор рейсов: будни, ежедневно или all для всех.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Путь для сохранения результата в JSON (по умолчанию data/trips.json).",
    )
    args = parser.parse_args()

    # Определяем, куда сохранить HTML, если он будет загружен по сети.
    html_save_target = args.save_html if args.save_html else DEFAULT_HTML_PATH
    # Загружаем страницу (из файла или по URL) и готовим данные.
    html = load_html(args.html, args.url, html_save_target if args.url else None)
    trips = parse_trips(html)
    trips = filter_trips(trips, args.filter_mode)

    request_time = datetime.now()
    # Собираем итоговое представление запроса с метаданными и рейсами.
    json_payload = {
        "requested_at": request_time.isoformat(),
        "filter": args.filter_mode,
        "trips": trips,
    }
    json_out_path = args.json_out or DEFAULT_JSON_PATH
    # Убеждаемся, что папка для JSON существует.
    json_out_path.parent.mkdir(parents=True, exist_ok=True)
    # Сохраняем структуру ответов в указанном JSON-файле.
    json_out_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Выводим краткий отчет о запросе и найденных рейсах.
    print(f"Request date: {request_time.strftime('%Y-%m-%d %H:%M:%S')}")
    for trip in trips:
        # Печатаем основное расписание: время, маршрут и метка дней.
        print(f"{trip['time']} {trip['from']} -> {trip['to']} ({trip['days_label']})")


if __name__ == "__main__":
    main()
