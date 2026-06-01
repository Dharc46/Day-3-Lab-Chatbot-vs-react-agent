"""
Tools cho Trợ Lý Đi Chợ Thông Minh.
Mỗi tool: nhận 1 str, trả 1 str.
"""

import json
from src.tools.mock_data import RECIPES, STORE_INVENTORY, SUBSTITUTIONS


# ==============================================================
# TOOL FUNCTIONS
# ==============================================================

def search_recipe(dish_name: str) -> str:
    """Tìm công thức nấu ăn theo tên món. Ưu tiên match chính xác trước."""
    if not dish_name or not dish_name.strip():
        return "Vui lòng nhập tên món ăn."

    query = dish_name.lower().strip()

    # Ưu tiên 1: match chính xác trong tên món
    for key, recipe in RECIPES.items():
        if query == recipe["name"].lower() or query == key:
            return json.dumps(recipe, ensure_ascii=False, indent=2)

    # Ưu tiên 2: query nằm trong tên món (vd: "phở" → "Phở Bò")
    for key, recipe in RECIPES.items():
        if query in recipe["name"].lower() or query in key:
            return json.dumps(recipe, ensure_ascii=False, indent=2)

    # Ưu tiên 3: bất kỳ từ nào match (vd: "gà kho" → "ga_kho_gung")
    for key, recipe in RECIPES.items():
        words = query.split()
        if len(words) > 1 and all(w in key or w in recipe["name"].lower() for w in words):
            return json.dumps(recipe, ensure_ascii=False, indent=2)

    available = ", ".join(r["name"] for r in RECIPES.values())
    return f"Không tìm thấy công thức cho '{dish_name}'. Các món có: {available}"


def check_inventory(item_name: str) -> str:
    """Kiểm tra nguyên liệu trong cửa hàng: giá, đơn vị, còn hàng không."""
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
    """Tính tổng tiền cho danh sách nguyên liệu (comma-separated).

    Lưu ý: tính theo giá đơn vị (vd: 1kg, 1 chai), chưa tính theo lượng
    thực tế trong recipe. Đây là ước tính chi phí mua nguyên liệu.
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
    """Gợi ý nguyên liệu thay thế khi hết hàng."""
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
# REGISTRY — agent dùng list này
# ==============================================================

# ★ ĐÂY LÀ V1

TOOL_REGISTRY = [
    {
        "name": "search_recipe",
        "description": "Tìm công thức nấu ăn. Input: tên món. Output: nguyên liệu, khẩu phần, thời gian.",
        "function": search_recipe,
    },
    {
        "name": "check_inventory",
        "description": "Kiểm tra nguyên liệu trong cửa hàng. Input: tên nguyên liệu. Output: giá, đơn vị, còn/hết.",
        "function": check_inventory,
    },
    {
        "name": "calculate_price",
        "description": "Tính tổng tiền. Input: nguyên liệu cách dấu phẩy. Output: chi tiết + tổng.",
        "function": calculate_price,
    },
    {
        "name": "suggest_substitute",
        "description": "Gợi ý thay thế khi hết hàng. Input: tên nguyên liệu. Output: lựa chọn thay thế.",
        "function": suggest_substitute,
    },
]