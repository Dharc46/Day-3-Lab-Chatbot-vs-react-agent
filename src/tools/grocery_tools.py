"""
Tools cho Trợ Lý Đi Chợ Thông Minh — V2.
Changes from v1:
  - search_recipe: added reverse matching (priority 4)
  - calculate_price: tracks out_of_stock separately, shows unit in breakdown
  - All tools: input validation for empty strings
  - TOOL_REGISTRY: descriptions more specific (v2)
"""

import json
from src.tools.mock_data import RECIPES, STORE_INVENTORY, SUBSTITUTIONS


# ==============================================================
# TOOL FUNCTIONS
# ==============================================================

def search_recipe(dish_name: str) -> str:
    """Find a recipe by dish name. Prioritizes exact > contains > multi-word > reverse match."""
    if not dish_name or not dish_name.strip():
        return "Vui lòng nhập tên món ăn."

    query = dish_name.lower().strip()

    # Priority 1: exact match
    for key, recipe in RECIPES.items():
        if query == recipe["name"].lower() or query == key:
            return json.dumps(recipe, ensure_ascii=False, indent=2)

    # Priority 2: query is substring of recipe name
    for key, recipe in RECIPES.items():
        if query in recipe["name"].lower() or query in key:
            return json.dumps(recipe, ensure_ascii=False, indent=2)

    # Priority 3: all query words match (e.g. "gà kho" → "ga_kho_gung")
    for key, recipe in RECIPES.items():
        words = query.split()
        if len(words) > 1 and all(w in key or w in recipe["name"].lower() for w in words):
            return json.dumps(recipe, ensure_ascii=False, indent=2)

    # Priority 4 (v2 fix): reverse match — recipe name words found in query
    # Handles cases like "đồ bún bò Huế" → contains "bún", "bò", "huế"
    for key, recipe in RECIPES.items():
        recipe_words = recipe["name"].lower().split()
        if all(w in query for w in recipe_words):
            return json.dumps(recipe, ensure_ascii=False, indent=2)

    available = ", ".join(r["name"] for r in RECIPES.values())
    return f"Không tìm thấy công thức cho '{dish_name}'. Các món có: {available}"


def check_inventory(item_name: str) -> str:
    """Check if an ingredient is available in store: price, unit, stock status."""
    if not item_name or not item_name.strip():
        return "Vui lòng nhập tên nguyên liệu."

    item = item_name.lower().strip()

    # Exact match
    if item in STORE_INVENTORY:
        info = STORE_INVENTORY[item]
        status = "CÒN HÀNG ✓" if info["in_stock"] else "HẾT HÀNG ✗"
        return f"{item}: {info['price']:,}đ/{info['unit']} — {status}"

    # Fuzzy match
    matches = [k for k in STORE_INVENTORY if item in k or k in item]
    if matches:
        return "\n".join(
            f"{m}: {STORE_INVENTORY[m]['price']:,}đ/{STORE_INVENTORY[m]['unit']} — "
            f"{'CÒN HÀNG ✓' if STORE_INVENTORY[m]['in_stock'] else 'HẾT HÀNG ✗'}"
            for m in matches
        )
    return f"Không tìm thấy '{item_name}' trong cửa hàng."


def calculate_price(items_str: str) -> str:
    """Calculate total estimated price for a comma-separated list of ingredients.

    Note: uses unit price (e.g. per kg, per bottle), not actual recipe quantity.
    """
    if not items_str or not items_str.strip():
        return "Vui lòng nhập danh sách nguyên liệu, cách nhau bởi dấu phẩy."

    items = [i.strip().lower() for i in items_str.split(",") if i.strip()]
    if not items:
        return "Danh sách nguyên liệu trống."

    total = 0
    breakdown = []
    not_found = []
    out_of_stock = []

    for item in items:
        if item in STORE_INVENTORY:
            info = STORE_INVENTORY[item]
            if info["in_stock"]:
                total += info["price"]
                breakdown.append(f"  {item}: {info['price']:,}đ/{info['unit']}")
            else:
                out_of_stock.append(item)
                breakdown.append(f"  {item}: HẾT HÀNG ✗")
        else:
            not_found.append(item)

    result = "CHI TIẾT:\n" + "\n".join(breakdown)
    if not_found:
        result += f"\nKhông tìm thấy: {', '.join(not_found)}"
    if out_of_stock:
        result += f"\nHết hàng: {', '.join(out_of_stock)} (cần tìm thay thế)"
    result += f"\n\nTỔNG ƯỚC TÍNH: {total:,}đ"
    return result


def suggest_substitute(item_name: str) -> str:
    """Suggest substitute ingredients when an item is out of stock."""
    if not item_name or not item_name.strip():
        return "Vui lòng nhập tên nguyên liệu cần thay thế."

    item = item_name.lower().strip()
    if item in SUBSTITUTIONS:
        return f"Thay thế cho '{item}': {', '.join(SUBSTITUTIONS[item])}"
    for key in SUBSTITUTIONS:
        if item in key or key in item:
            return f"Thay thế cho '{key}': {', '.join(SUBSTITUTIONS[key])}"
    return f"Không có gợi ý thay thế cho '{item_name}'."


# ==============================================================
# REGISTRY V2 — more specific descriptions
# ==============================================================

TOOL_REGISTRY = [
    {
        "name": "search_recipe",
        "description": (
            "Search for a Vietnamese recipe by dish name. "
            "Input: dish name in Vietnamese (e.g. 'phở bò', 'bún bò Huế', 'gà kho gừng'). "
            "Output: JSON with name, servings (int), ingredients (list of {item, quantity}), time. "
            "Returns error message if not found, with list of available dishes."
        ),
        "function": search_recipe,
    },
    {
        "name": "check_inventory",
        "description": (
            "Check ONE ingredient in the store inventory. "
            "Input: ingredient name in Vietnamese (e.g. 'thịt bò', 'giò heo'). "
            "Output: price in VNĐ, unit, and stock status (CÒN HÀNG / HẾT HÀNG). "
            "Only check one ingredient per call."
        ),
        "function": check_inventory,
    },
    {
        "name": "calculate_price",
        "description": (
            "Calculate total estimated cost for a list of ingredients. "
            "Input: comma-separated ingredient names (e.g. 'thịt bò, hành tây, gừng'). "
            "Output: price breakdown per item and total in VNĐ. "
            "Also flags out-of-stock and not-found items."
        ),
        "function": calculate_price,
    },
    {
        "name": "suggest_substitute",
        "description": (
            "Suggest replacement ingredients when something is out of stock. "
            "Input: name of the out-of-stock ingredient (e.g. 'giò heo'). "
            "Output: list of 2-3 alternative ingredients."
        ),
        "function": suggest_substitute,
    },
]