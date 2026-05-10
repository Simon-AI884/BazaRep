import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE_DIR / "data" / "pumps_catalog.json"


def load_pumps_catalog() -> list[dict[str, Any]]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def extract_numbers_near_meters(text: str) -> list[float]:
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:м|метр|метрів|метров)", text)
    return [float(value.replace(",", ".")) for value in matches]


def extract_depth_m(text: str) -> float | None:
    lowered = text.lower()

    depth_words = [
        "глибина", "глубина", "води на", "вода на", "дзеркало", "зеркало",
        "до води", "до воды", "свердловина", "скважина", "колодязь", "колодец"
    ]

    numbers = extract_numbers_near_meters(lowered)

    if not numbers:
        return None

    for word in depth_words:
        if word in lowered:
            return numbers[0]

    return None


def detect_preferred_installation(text: str) -> str | None:
    if any(word in text for word in ["поверхнев", "поверхност"]):
        return "surface"

    if any(word in text for word in ["занур", "погруж", "глибинн", "глубинн"]):
        return "submersible"

    if any(word in text for word in ["насосна станц", "насосная станц", "станцію", "станцию"]):
        return "pump_station"

    return None


def detect_water_quality(text: str) -> str | None:
    if any(word in text for word in ["каналіз", "канализ", "фекал", "туалет", "стоки"]):
        return "sewage"

    if any(word in text for word in ["бруд", "гряз", "мул", "ил", "болото"]):
        return "dirty"

    if any(word in text for word in ["хім", "хим", "морськ", "морск", "солона", "соленая"]):
        return "chemical"

    if any(word in text for word in ["чист", "питна", "питьевая"]):
        return "clean"

    return None


def detect_source_type(text: str) -> str | None:
    if any(word in text for word in ["свердлов", "скваж"]):
        return "borehole"

    if any(word in text for word in ["колод"]):
        return "well"

    if any(word in text for word in ["ємність", "емкость", "бак", "резервуар", "цистерн"]):
        return "tank"

    if any(word in text for word in ["ставок", "пруд", "водойм", "річка", "река"]):
        return "pond"

    if any(word in text for word in ["підвал", "подвал", "яма", "котлован"]):
        return "basement"

    if any(word in text for word in ["басейн", "бассейн"]):
        return "pool"

    if any(word in text for word in ["водопровід", "водопровод", "трубопровід", "трубопровод"]):
        return "pipeline"

    if any(word in text for word in ["опалення", "отоплен"]):
        return "heating"

    if any(word in text for word in ["каналіз", "канализ", "фекал", "стоки"]):
        return "sewage"

    return None


def detect_application(text: str) -> str | None:
    if any(word in text for word in ["полив", "зрош", "орош", "город", "сад", "теплиц", "парник"]):
        return "irrigation"

    if any(word in text for word in ["будинок", "дом", "дач", "кухня", "душ", "умивальник", "водопостач"]):
        return "water_supply"

    if any(word in text for word in ["дренаж", "відкач", "откач", "затоп", "підвал", "подвал"]):
        return "drainage"

    if any(word in text for word in ["каналіз", "канализ", "фекал", "туалет", "стоки"]):
        return "sewage"

    if any(word in text for word in ["басейн", "бассейн"]):
        return "pool"

    if any(word in text for word in ["опалення", "отоплен", "циркуляц"]):
        return "heating"

    if any(word in text for word in ["тиск", "давление", "напор", "слабкий тиск", "слабое давление"]):
        return "pressure_boosting"

    return None


def detect_possible_categories(
    source_type: str | None,
    application: str | None,
    water_quality: str | None
) -> list[str]:
    categories: list[str] = []

    if source_type == "borehole":
        categories.extend(["borehole_pump"])

    if source_type == "well":
        categories.extend([
            "surface_pump",
            "pump_station",
            "borehole_pump",
            "semi_submersible_pump",
            "submersible_pump"
        ])

    if source_type in ["tank", "cistern"]:
        categories.extend([
            "surface_pump",
            "pump_station",
            "submersible_pump"
        ])

    if source_type == "pond":
        categories.extend([
            "surface_pump",
            "motor_pump",
            "drainage_pump"
        ])

    if source_type == "basement" or application == "drainage":
        categories.extend(["drainage_pump"])

    if source_type == "pool" or application == "pool":
        categories.extend(["pool_pump"])

    if source_type == "heating" or application == "heating":
        categories.extend(["circulation_pump"])

    if source_type == "pipeline" or application == "pressure_boosting":
        categories.extend([
            "pressure_booster_pump",
            "pump_station"
        ])

    if source_type == "sewage" or application == "sewage" or water_quality == "sewage":
        categories.extend(["sewage_pump"])

    if water_quality == "dirty":
        categories.extend([
            "drainage_pump",
            "motor_pump"
        ])

    if water_quality == "chemical":
        categories.extend([
            "motor_pump",
            "industrial_pump"
        ])

    return list(dict.fromkeys(categories))


def detect_pump_scenario(user_message: str) -> dict[str, Any]:
    text = user_message.lower()

    preferred_installation = detect_preferred_installation(text)
    source_type = detect_source_type(text)
    application = detect_application(text)
    water_quality = detect_water_quality(text)
    depth_m = extract_depth_m(text)

    possible_categories = detect_possible_categories(
        source_type=source_type,
        application=application,
        water_quality=water_quality
    )

    selected_categories = possible_categories.copy()
    selected_installation_type = None

    if preferred_installation == "surface":
        selected_installation_type = "surface"
        selected_categories = [
            category for category in possible_categories
            if category in ["surface_pump", "pump_station", "pressure_booster_pump"]
        ]

    elif preferred_installation == "submersible":
        selected_installation_type = "submersible"
        selected_categories = [
            category for category in possible_categories
            if category in [
                "borehole_pump",
                "drainage_pump",
                "sewage_pump",
                "semi_submersible_pump",
                "submersible_pump"
            ]
        ]

    elif preferred_installation == "pump_station":
        selected_installation_type = "surface"
        selected_categories = ["pump_station"]

    needs_installation_clarification = False

    if not preferred_installation:
        if source_type in ["well", "tank", "cistern", "pond"]:
            needs_installation_clarification = True

        if len(possible_categories) > 1:
            needs_installation_clarification = True

    return {
        "text": text,
        "source_type": source_type,
        "application": application,
        "water_quality": water_quality,
        "depth_m": depth_m,
        "preferred_installation": preferred_installation,
        "selected_installation_type": selected_installation_type,
        "possible_categories": possible_categories,
        "selected_categories": selected_categories,
        "needs_installation_clarification": needs_installation_clarification
    }


def score_pump(pump: dict[str, Any], scenario: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    score = 0
    reasons: list[str] = []
    warnings: list[str] = []

    text = scenario["text"]

    article = str(pump.get("article", "")).lower()
    model = str(pump.get("model", "")).lower()

    if article and article in text:
        score += 100
        reasons.append("збіг за артикулом")

    if model and model in text:
        score += 100
        reasons.append("збіг за моделлю")

    selected_categories = scenario.get("selected_categories", [])
    possible_categories = scenario.get("possible_categories", [])

    if selected_categories:
        if pump.get("main_category") in selected_categories:
            score += 35
            reasons.append("підходить за категорією")
        else:
            score -= 25
            warnings.append("категорія може не відповідати задачі")
    elif possible_categories:
        if pump.get("main_category") in possible_categories:
            score += 20
            reasons.append("потенційно підходить за категорією")

    selected_installation_type = scenario.get("selected_installation_type")

    if selected_installation_type:
        if pump.get("installation_type") == selected_installation_type:
            score += 20
            reasons.append("підходить за бажаним типом встановлення")
        else:
            score -= 30
            warnings.append("не відповідає бажаному типу встановлення")

    source_type = scenario.get("source_type")

    if source_type:
        if source_type in pump.get("source_types", []):
            score += 20
            reasons.append("підходить за джерелом води")
        else:
            score -= 8
            warnings.append("джерело води не вказане серед основних для цього насоса")

    application = scenario.get("application")

    if application:
        if application in pump.get("applications", []):
            score += 20
            reasons.append("підходить за задачею")
        else:
            score -= 8
            warnings.append("задача не вказана серед основних для цього насоса")

    water_quality = scenario.get("water_quality")

    if water_quality:
        if pump.get("water_quality") == water_quality:
            score += 20
            reasons.append("підходить за якістю води")
        else:
            score -= 35
            warnings.append("може не підходити за якістю води")

    depth_m = scenario.get("depth_m")
    suction_depth_m = pump.get("suction_depth_m")

    if depth_m and pump.get("installation_type") == "surface":
        if suction_depth_m and depth_m <= suction_depth_m:
            score += 15
            reasons.append("підходить за висотою всмоктування")
        else:
            score -= 40
            warnings.append("поверхневий насос може не підняти воду з такої глибини")

    if source_type == "borehole" and pump.get("installation_type") == "surface":
        score -= 40
        warnings.append("для свердловини зазвичай потрібен занурювальний свердловинний насос")

    if water_quality in ["dirty", "sewage"] and pump.get("water_quality") == "clean":
        score -= 50
        warnings.append("насос для чистої води не можна використовувати для брудної або каналізаційної води")

    searchable_text = " ".join([
        str(pump.get("main_category_name", "")),
        str(pump.get("sub_category_name", "")),
        str(pump.get("usage", "")),
        str(pump.get("limitations", "")),
        str(pump.get("water_type_text", "")),
        " ".join(pump.get("source_type_names", [])),
        " ".join(pump.get("application_names", []))
    ]).lower()

    for keyword in [
        "колод", "свердлов", "скваж", "полив", "город", "сад", "дач",
        "будинок", "дом", "дренаж", "каналіз", "басейн", "опалення",
        "отоплен", "тиск", "давление"
    ]:
        if keyword in text and keyword in searchable_text:
            score += 3

    return score, reasons, warnings


def find_relevant_pumps(user_message: str, limit: int = 8) -> dict[str, Any]:
    catalog = load_pumps_catalog()
    scenario = detect_pump_scenario(user_message)

    results = []

    for pump in catalog:
        score, reasons, warnings = score_pump(pump, scenario)

        if score > 0:
            pump_copy = pump.copy()
            pump_copy["_score"] = score
            pump_copy["_reasons"] = reasons
            pump_copy["_warnings"] = warnings
            results.append(pump_copy)

    results.sort(key=lambda item: item["_score"], reverse=True)

    return {
        "scenario": scenario,
        "pumps": results[:limit]
    }


def format_scenario_for_ai(scenario: dict[str, Any]) -> str:
    return f"""
Визначений сценарій:
- Джерело води: {scenario.get("source_type")}
- Задача: {scenario.get("application")}
- Якість води: {scenario.get("water_quality")}
- Глибина / рівень води: {scenario.get("depth_m")} м
- Бажаний тип встановлення: {scenario.get("preferred_installation")}
- Можливі категорії: {", ".join(scenario.get("possible_categories", []))}
- Категорії для пошуку: {", ".join(scenario.get("selected_categories", []))}
- Потрібно уточнити тип насоса: {scenario.get("needs_installation_clarification")}
"""


def format_pumps_for_ai(pumps: list[dict[str, Any]]) -> str:
    if not pumps:
        return "За запитом не знайдено конкретних товарів у каталозі."

    result = ""

    for index, pump in enumerate(pumps, start=1):
        product_url = pump.get("product_url") or "посилання не додано"

        result += f"""
Варіант {index}:
Рейтинг підбору: {pump.get("_score")}
Причини підбору: {", ".join(pump.get("_reasons", []))}
Попередження: {", ".join(pump.get("_warnings", []))}

Артикул: {pump.get("article")}
Модель: {pump.get("model")}
Бренд: {pump.get("brand")}

Категорія: {pump.get("main_category_name")}
Підкатегорія: {pump.get("sub_category_name")}
Тип встановлення: {pump.get("installation_type_name")}

Джерела води: {", ".join(pump.get("source_type_names", []))}
Задачі: {", ".join(pump.get("application_names", []))}
Якість води: {pump.get("water_quality_name")}
Не підходить для: {", ".join(pump.get("not_for_names", []))}

Живлення: {pump.get("phase")}
Потужність: {pump.get("power_kw")} кВт
Максимальна подача: {pump.get("q_max_l_min")} л/хв
Максимальний напір: {pump.get("h_max_m")} м
Максимальна висота всмоктування: {pump.get("suction_depth_m")} м

Опис застосування: {pump.get("usage")}
Обмеження: {pump.get("limitations")}
Гарантія: {pump.get("warranty_months")} місяців
Посилання на товар: {product_url}
"""
    return result