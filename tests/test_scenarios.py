"""
10 test cases: 2 simple, 5 multi-step, 3 edge.
Dùng cho run_tests.py để so sánh chatbot vs agent.
"""

TEST_CASES = [
    # --- SIMPLE (chatbot cũng trả lời được) ---
    {
        "id": "S1",
        "input": "Phở bò nấu mất bao lâu?",
        "type": "simple",
        "expected": "thời gian nấu",
    },
    {
        "id": "S2",
        "input": "Cơm tấm gồm những gì?",
        "type": "simple",
        "expected": "liệt kê nguyên liệu cơ bản",
    },

    # --- MULTI-STEP (cần agent) ---
    {
        "id": "M1",
        "input": "Tôi muốn nấu phở bò cho 4 người, kiểm tra nguyên liệu và tổng bao nhiêu tiền?",
        "type": "multi_step",
        "expected": "recipe → check → calculate",
    },
    {
        "id": "M2",
        "input": "Nấu bún bò Huế cần gì? Nguyên liệu hết thì gợi ý thay thế giúp tôi.",
        "type": "multi_step",
        "expected": "recipe → check → substitute (giò heo, mắm ruốc)",
    },
    {
        "id": "M3",
        "input": "Tôi có 200,000đ, muốn nấu cơm tấm cho 2 người. Đủ tiền không?",
        "type": "multi_step",
        "expected": "recipe → calculate → so sánh budget",
    },
    {
        "id": "M4",
        "input": "Nấu canh chua cá cần gì? Tính giá giúp tôi.",
        "type": "multi_step",
        "expected": "recipe → calculate",
    },
    {
        "id": "M5",
        "input": "Sinh viên có 150,000đ. Gợi ý 1 món tiết kiệm nhất?",
        "type": "multi_step",
        "expected": "compare recipes → pick cheapest",
    },

    # --- EDGE CASES ---
    {
        "id": "E1",
        "input": "Nấu sushi được không?",
        "type": "edge",
        "expected": "không tìm thấy → thông báo",
    },
    {
        "id": "E2",
        "input": "Giá thịt bò bao nhiêu? Còn đùi gà?",
        "type": "edge",
        "expected": "check 2 items",
    },
    {
        "id": "E3",
        "input": "Bún bò Huế cho 8 người hết bao nhiêu?",
        "type": "edge",
        "expected": "recipe 4 người → x2 → calculate",
    },
]
