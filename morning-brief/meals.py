"""
Google Sheets integration for Network School meal menu.
Fetches daily meal recommendations and filters by dietary restrictions.
"""

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json
from functools import lru_cache

# Google Sheets configuration
SHEETS_ID = "1ZxHmQCSbIKs895uWCM9UKQdXyPVv9jaPh9ErSvSA9x0"
FULL_MENU_TAB_ID = 1656742956      # Full meals tab
PER_100G_TAB_ID = 1278865001        # Per-100g ingredients tab

# Dietary restrictions
FORBIDDEN_INGREDIENTS = {"seafood", "peanuts", "nuts", "fish", "shrimp", "crab", "lobster"}

TZ = pytz.timezone("Asia/Kuala_Lumpur")


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
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Fallback to credentials.json file (for local testing)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", scope
        )

    return gspread.authorize(creds)


@lru_cache(maxsize=32)
def get_per_100g_nutrients(item_name):
    """
    Get per-100g macros for an ingredient.
    Returns: {'cal': X, 'protein': X, 'carbs': X, 'fat': X, 'fiber': X}
    """
    try:
        client = get_sheets_client()
        sheet = client.open_by_key(SHEETS_ID)

        # Find worksheet by tab ID
        per_100g_sheet = None
        for ws in sheet.worksheets():
            if ws.id == PER_100G_TAB_ID:
                per_100g_sheet = ws
                break

        if not per_100g_sheet:
            print(f"Warning: Per-100g sheet not found (tab {PER_100G_TAB_ID})")
            return None

        # Get all values
        all_values = per_100g_sheet.get_all_values()
        if not all_values or len(all_values) < 2:
            return None

        # Assuming: headers in row 0, data in rows 1+
        # Columns: Item, Calories, Protein (g), Carbs (g), Fat (g), Fiber (g)
        headers = all_values[0]
        try:
            item_idx = headers.index("Item")
            cal_idx = headers.index("Calories")
            protein_idx = headers.index("Protein (g)")
            carbs_idx = headers.index("Carbs (g)")
            fat_idx = headers.index("Fat (g)")
            fiber_idx = headers.index("Fiber (g)")
        except ValueError:
            print(f"Warning: Expected columns not found in per-100g sheet")
            return None

        # Find matching item
        for row in all_values[1:]:
            if row and row[item_idx].lower() == item_name.lower():
                try:
                    return {
                        'cal': float(row[cal_idx]) if row[cal_idx] else 0,
                        'protein': float(row[protein_idx]) if row[protein_idx] else 0,
                        'carbs': float(row[carbs_idx]) if row[carbs_idx] else 0,
                        'fat': float(row[fat_idx]) if row[fat_idx] else 0,
                        'fiber': float(row[fiber_idx]) if row[fiber_idx] else 0,
                    }
                except (ValueError, IndexError):
                    pass

        return None

    except Exception as e:
        print(f"Error fetching per-100g nutrients for {item_name}: {e}")
        return None


def fetch_menu(day_of_week, meal_type):
    """
    Fetch menu for a specific day and meal type.

    day_of_week: 0-6 (Monday-Sunday) or name ("Monday", "Tuesday", etc.)
    meal_type: "breakfast", "lunch", or "dinner"

    Returns: [
        {
            'name': 'Pesto Chicken',
            'description': 'Optional description',
            'ingredients': ['chicken', 'pesto', 'rice', ...]
        },
        ...
    ]
    """
    try:
        # Normalize day of week
        if isinstance(day_of_week, str):
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_of_week = days.index(day_of_week)
        elif isinstance(day_of_week, int):
            day_of_week = day_of_week % 7

        client = get_sheets_client()
        sheet = client.open_by_key(SHEETS_ID)

        # Find full menu worksheet
        menu_sheet = None
        for ws in sheet.worksheets():
            if ws.id == FULL_MENU_TAB_ID:
                menu_sheet = ws
                break

        if not menu_sheet:
            print(f"Warning: Menu sheet not found (tab {FULL_MENU_TAB_ID})")
            return []

        all_values = menu_sheet.get_all_values()
        if not all_values or len(all_values) < 2:
            return []

        # Expected structure:
        # Headers: Day, Meal, Item, Ingredients
        headers = all_values[0]
        try:
            day_idx = headers.index("Day")
            meal_idx = headers.index("Meal")
            item_idx = headers.index("Item")
            ingr_idx = headers.index("Ingredients")
        except ValueError:
            print("Warning: Expected columns not found in menu sheet")
            return []

        # Get day name
        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_of_week]

        # Filter rows for this day + meal type
        items = []
        for row in all_values[1:]:
            if not row:
                continue
            if (row[day_idx].lower() == day_name.lower() and
                row[meal_idx].lower() == meal_type.lower()):
                item_name = row[item_idx]
                ingredients = [i.strip() for i in row[ingr_idx].split(",") if i.strip()]
                items.append({
                    'name': item_name,
                    'ingredients': ingredients
                })

        return items

    except Exception as e:
        print(f"Error fetching menu for {day_of_week}/{meal_type}: {e}")
        return []


def filter_menu(items):
    """
    Filter out items containing forbidden ingredients (seafood, peanuts, nuts).

    Returns: [{'name': ..., 'ingredients': ...}, ...]
    """
    filtered = []
    for item in items:
        ingredients_lower = [ing.lower() for ing in item.get('ingredients', [])]

        # Check if any forbidden ingredient is in this item
        has_forbidden = False
        for ingredient in ingredients_lower:
            for forbidden in FORBIDDEN_INGREDIENTS:
                if forbidden in ingredient:
                    has_forbidden = True
                    break
            if has_forbidden:
                break

        if not has_forbidden:
            filtered.append(item)

    return filtered


def calculate_macros_for_scoops(item_name, scoops):
    """
    Calculate total macros for a given number of scoops (100g per scoop).
    Returns: {'cal': X, 'protein': X, ...} or None if item not found
    """
    nutrients = get_per_100g_nutrients(item_name)
    if not nutrients:
        return None

    return {
        'cal': nutrients['cal'] * scoops,
        'protein': nutrients['protein'] * scoops,
        'carbs': nutrients['carbs'] * scoops,
        'fat': nutrients['fat'] * scoops,
        'fiber': nutrients['fiber'] * scoops,
    }


def rank_and_recommend(items, remaining_targets):
    """
    Rank items by protein density and suggest scoop counts.

    remaining_targets: {
        'cal': 700,      # remaining calories
        'protein': 50,   # remaining protein
        'carbs': 80,
        'fat': 20,
        'fiber': 5
    }

    Returns: [
        {
            'name': 'Pesto Chicken',
            'scoops': 2.5,
            'cal': 780,
            'protein': 62,
            'carbs': 75,
            'fat': 25,
            'fiber': 4,
            'protein_per_cal': 0.079
        },
        ...
    ]
    Sorted by protein density (highest first).
    """
    recommendations = []

    for item in items:
        nutrients = get_per_100g_nutrients(item['name'])
        if not nutrients:
            continue

        # Calculate ideal scoops based on remaining protein target
        # 1 scoop = 100g
        remaining_protein = remaining_targets.get('protein', 50)
        protein_per_scoop = nutrients['protein']

        if protein_per_scoop > 0:
            ideal_scoops = remaining_protein / protein_per_scoop
            # Round to nearest 0.5 scoop
            scoops = round(ideal_scoops * 2) / 2
            scoops = max(1, scoops)  # At least 1 scoop
        else:
            scoops = 1

        # Calculate actual macros for this scoop count
        macros = calculate_macros_for_scoops(item['name'], scoops)
        if not macros:
            continue

        protein_per_cal = nutrients['protein'] / nutrients['cal'] if nutrients['cal'] > 0 else 0

        recommendations.append({
            'name': item['name'],
            'scoops': scoops,
            'cal': round(macros['cal']),
            'protein': round(macros['protein'], 1),
            'carbs': round(macros['carbs'], 1),
            'fat': round(macros['fat'], 1),
            'fiber': round(macros['fiber'], 1),
            'protein_per_cal': round(protein_per_cal, 3)
        })

    # Sort by protein density (highest first)
    recommendations.sort(key=lambda x: x['protein_per_cal'], reverse=True)
    return recommendations


def get_todays_meal_recommendation(meal_type):
    """
    Get today's meal recommendation (breakfast, lunch, or dinner).

    Returns: {
        'meal_type': 'lunch',
        'recommendation': [
            {'name': '...', 'scoops': X, 'cal': X, ...},
            ...
        ]
    }
    """
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    today = datetime.now(tz)
    day_of_week = today.weekday()  # 0-6, Monday-Sunday

    menu = fetch_menu(day_of_week, meal_type)
    filtered = filter_menu(menu)

    # For now, use default remaining targets
    # In production, this should come from health_db.get_today_totals()
    remaining_targets = {
        'cal': 700,
        'protein': 50,
        'carbs': 80,
        'fat': 20,
        'fiber': 5
    }

    ranked = rank_and_recommend(filtered, remaining_targets)

    return {
        'meal_type': meal_type,
        'day': today.strftime("%A"),
        'recommendation': ranked[:3]  # Top 3 recommendations
    }
