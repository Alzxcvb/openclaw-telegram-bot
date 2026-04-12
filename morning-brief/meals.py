"""
Google Sheets integration for Network School meal menu.
Fetches daily meal recommendations from the current workbook layout.
"""

import os
import json
from datetime import datetime

import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets configuration
SHEETS_ID = "1ZxHmQCSbIKs895uWCM9UKQdXyPVv9jaPh9ErSvSA9x0"
LUNCH_SHEET_TITLE = "Lunch"
DINNER_SHEET_TITLE = "Dinner"

# Dietary restrictions
FORBIDDEN_INGREDIENTS = {"seafood", "peanuts", "nuts", "fish", "shrimp", "crab", "lobster"}

TZ = pytz.timezone("Asia/Kuala_Lumpur")
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_HEADERS = {day.upper() for day in DAY_NAMES}
EXCLUDED_CATEGORIES = {"dressing", "dressings", "topping", "toppings", "beverage", "beverages", "sides"}


def get_sheets_client():
    """
    Initialize Google Sheets API client.
    Requires GOOGLE_SHEETS_CREDENTIALS env var or credentials.json file.
    """
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

    return gspread.authorize(creds)


def _norm(value):
    return " ".join((value or "").strip().lower().split())


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _worksheet_by_title(sheet, title):
    target = _norm(title)
    for ws in sheet.worksheets():
        if _norm(ws.title) == target:
            return ws
    return None


def _is_day_header(row):
    return bool(row and row[0].strip().upper() in DAY_HEADERS)


def _find_day_block(rows, day_name):
    target = day_name.upper()
    start = None
    for idx, row in enumerate(rows):
        if row and row[0].strip().upper() == target:
            start = idx + 1
            break

    if start is None:
        return []

    block = []
    for row in rows[start:]:
        if _is_day_header(row):
            break
        if any(cell.strip() for cell in row):
            block.append(row)
    return block


def _is_protein_category(category):
    label = _norm(category)
    if not label:
        return False
    if label in EXCLUDED_CATEGORIES:
        return False
    return "protein" in label or label in {"chicken", "beef", "vegetarian", "vegan"}


def _extract_macros(values):
    if len(values) < 5:
        return None
    parsed = [_to_float(value) for value in values]
    if any(value is None for value in parsed):
        return None
    cal, carbs, protein, fat, fiber = parsed
    return {
        "cal": cal,
        "carbs": carbs,
        "protein": protein,
        "fat": fat,
        "fiber": fiber,
    }


def fetch_menu(day_of_week, meal_type):
    """
    Fetch menu options for a specific day and meal type from the current workbook.
    """
    try:
        if isinstance(day_of_week, str):
            day_name = day_of_week
        else:
            day_name = DAY_NAMES[day_of_week % 7]

        print(f"[meals] Fetching {meal_type} menu for {day_name}")
        client = get_sheets_client()
        sheet = client.open_by_key(SHEETS_ID)

        if meal_type.lower() == "lunch":
            items = _fetch_lunch_menu(sheet, day_name)
        elif meal_type.lower() == "dinner":
            items = _fetch_dinner_menu(sheet, day_name)
        else:
            items = []

        print(f"[meals] Got {len(items)} items for {day_name} {meal_type}")
        if not items:
            # Dump sheet tab names for debugging
            tabs = [ws.title for ws in sheet.worksheets()]
            print(f"[meals] Available sheet tabs: {tabs}")
        return items
    except Exception as e:
        print(f"[meals] ERROR fetching menu for {day_of_week}/{meal_type}: {e}")
        import traceback
        traceback.print_exc()
        return []


def _fetch_dinner_menu(sheet, day_name):
    """Parse the current Dinner worksheet, which is organized by day sections."""
    ws = _worksheet_by_title(sheet, DINNER_SHEET_TITLE)
    if not ws:
        print(f"Warning: Dinner sheet not found ({DINNER_SHEET_TITLE})")
        return []

    rows = ws.get_all_values()
    print(f"[meals] Dinner sheet has {len(rows)} rows total")
    block = _find_day_block(rows, day_name)
    print(f"[meals] Dinner block for {day_name}: {len(block)} rows")
    if block and len(block) > 0:
        print(f"[meals] First dinner row sample: {block[0][:8]}")
    items = []
    current_category = ""

    for row in block:
        if len(row) < 6:
            continue

        first = row[0].strip()
        second = row[1].strip() if len(row) > 1 else ""

        if second == "Item":
            continue

        if _extract_macros(row[2:7]):
            current_category = first or current_category
            item_name = second
            macros = _extract_macros(row[2:7])
        elif _extract_macros(row[1:6]):
            item_name = first
            macros = _extract_macros(row[1:6])
        else:
            continue

        if not item_name or not macros:
            continue
        if not _is_protein_category(current_category):
            print(f"[meals] Skipping '{item_name}' — category '{current_category}' not protein")
            continue

        items.append(
            {
                "name": item_name,
                "category": current_category,
                "serving_unit": "scoop",
                "serving_size_g": 100,
                **macros,
            }
        )

    return items


def _fetch_lunch_menu(sheet, day_name):
    """Parse the current Lunch worksheet, which stores complete meal combinations."""
    ws = _worksheet_by_title(sheet, LUNCH_SHEET_TITLE)
    if not ws:
        print(f"Warning: Lunch sheet not found ({LUNCH_SHEET_TITLE})")
        return []

    rows = ws.get_all_values()
    print(f"[meals] Lunch sheet has {len(rows)} rows total")
    block = _find_day_block(rows, day_name)
    print(f"[meals] Lunch block for {day_name}: {len(block)} rows")
    if block and len(block) > 0:
        print(f"[meals] First lunch row sample: {block[0][:10]}")
    items = []
    current_category = ""
    current_item = ""
    current_portion = ""

    for row in block:
        if len(row) < 7:
            continue

        first = row[0].strip()
        second = row[1].strip() if len(row) > 1 else ""
        third = row[2].strip() if len(row) > 2 else ""

        if second == "Item":
            continue

        category = current_category
        item_name = ""
        portion = current_portion
        base = ""
        macros = None

        if third in {"R", "D"}:
            macros = _extract_macros(row[4:9])
            if macros:
                current_category = first or current_category
                current_item = second
                current_portion = third
                category = current_category
                item_name = current_item
                portion = current_portion
                base = row[3].strip()
        elif second in {"R", "D"}:
            macros = _extract_macros(row[3:8])
            if macros:
                item_name = current_item
                portion = second
                current_portion = second
                base = third
        else:
            macros = _extract_macros(row[2:7])
            if macros:
                item_name = current_item
                base = second

        if not item_name or not macros or not _is_protein_category(category):
            continue

        portion_label = "double" if portion == "D" else "regular"
        display_name = f"{item_name} ({base}, {portion_label})" if base else f"{item_name} ({portion_label})"

        items.append(
            {
                "name": display_name,
                "category": category,
                "serving_unit": "plate",
                "portion": portion,
                **macros,
            }
        )

    return items


def filter_menu(items):
    """
    Filter out items whose name or category contains forbidden ingredients.
    Checks the item name and category since the sheet doesn't have a separate
    ingredients column.
    """
    filtered = []
    for item in items:
        name_lower = item.get("name", "").lower()
        category_lower = item.get("category", "").lower()
        combined = f"{name_lower} {category_lower}"

        has_forbidden = any(f in combined for f in FORBIDDEN_INGREDIENTS)
        if not has_forbidden:
            filtered.append(item)
        else:
            print(f"[meals] Filtered out: {item.get('name')} (allergen match)")

    return filtered


def rank_and_recommend(items, remaining_targets):
    """
    Rank items by protein density and size the recommendation when 100g scoop
    data is available.
    """
    recommendations = []

    for item in items:
        cal = float(item.get("cal", 0) or 0)
        protein = float(item.get("protein", 0) or 0)
        carbs = float(item.get("carbs", 0) or 0)
        fat = float(item.get("fat", 0) or 0)
        fiber = float(item.get("fiber", 0) or 0)
        serving_unit = item.get("serving_unit", "scoop")

        if cal <= 0 or protein <= 0:
            continue

        if serving_unit == "scoop":
            remaining_protein = remaining_targets.get("protein", 50)
            ideal_servings = remaining_protein / protein if protein > 0 else 1
            servings = max(1, round(ideal_servings * 2) / 2)
        else:
            servings = 1

        protein_per_cal = protein / cal if cal > 0 else 0
        recommendations.append(
            {
                "name": item["name"],
                "scoops": servings,
                "serving_unit": serving_unit,
                "cal": round(cal * servings),
                "protein": round(protein * servings, 1),
                "carbs": round(carbs * servings, 1),
                "fat": round(fat * servings, 1),
                "fiber": round(fiber * servings, 1),
                "protein_per_cal": round(protein_per_cal, 3),
            }
        )

    recommendations.sort(key=lambda x: x["protein_per_cal"], reverse=True)
    return recommendations


def get_todays_meal_recommendation(meal_type):
    """
    Get today's meal recommendation (breakfast, lunch, or dinner).
    """
    today = datetime.now(TZ)
    day_of_week = today.weekday()

    menu = fetch_menu(day_of_week, meal_type)
    filtered = filter_menu(menu)

    from health_db import get_today_totals

    totals = get_today_totals()
    remaining_targets = {
        "cal": max(0, 2500 - (totals["cal"] + totals["manual_adjustment_cal"])),
        "protein": max(0, 150 - (totals["protein"] + totals["manual_adjustment_protein"])),
        "carbs": max(0, 315 - totals["carbs"]),
        "fat": max(0, 75 - totals["fat"]),
        "fiber": max(0, 27 - totals["fiber"]),
    }

    ranked = rank_and_recommend(filtered, remaining_targets)

    return {
        "meal_type": meal_type,
        "day": today.strftime("%A"),
        "recommendation": ranked[:3],
    }
