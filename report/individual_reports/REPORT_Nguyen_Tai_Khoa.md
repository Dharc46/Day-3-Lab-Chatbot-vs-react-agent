# Báo Cáo Cá Nhân: Lab 3 — Chatbot vs ReAct Agent

- **Họ tên**: Nguyễn Tài Khoa
- **MSSV**: 2A202600682
- **Ngày**: 01/06/2026
- **Vai trò**: B — Backend Data (Tools + Chatbot Baseline)

---

## I. Đóng Góp Kỹ Thuật (15 điểm)

### Modules đã triển khai

**1. `src/tools/mock_data.py`** — Data layer tách riêng khỏi logic

Thiết kế và xây dựng toàn bộ mock database cho hệ thống:
- `RECIPES`: 5 công thức Việt Nam (Phở Bò, Bún Bò Huế, Cơm Tấm, Gà Kho Gừng, Canh Chua Cá) với đầy đủ ingredients, servings, time
- `STORE_INVENTORY`: 35+ nguyên liệu với giá thực tế VNĐ, đơn vị, trạng thái kho
- `SUBSTITUTIONS`: 10 mapping thay thế nguyên liệu
- Thiết kế có chủ đích: `giò heo` và `mắm ruốc` đặt `in_stock=False` để tạo test case buộc agent gọi `suggest_substitute`

Quyết định tách `mock_data.py` riêng khỏi `grocery_tools.py` để dễ swap sang real database sau — đây là design pattern Data Access Layer phổ biến trong production.

**2. `src/tools/grocery_tools.py`** — 4 tool functions, trải qua 3 phiên bản

| Phiên bản | Thay đổi chính |
| :--- | :--- |
| v1 | 4 tools cơ bản, fuzzy matching đơn giản, single-item input |
| v2 | Thêm reverse matching cho search_recipe, input validation, better descriptions |
| v3 | Tất cả tools hỗ trợ comma-separated input (multi-item) |

Chi tiết từng tool:
- `search_recipe()`: fuzzy matching 4 mức ưu tiên (exact → contains → multi-word → reverse)
- `check_inventory()`: exact match + fuzzy match, hỗ trợ kiểm tra nhiều items cùng lúc
- `calculate_price()`: tính tổng ước tính, phân tách out_of_stock vs not_found, ghi rõ "TỔNG ƯỚC TÍNH"
- `suggest_substitute()`: tra bảng thay thế với fuzzy fallback, xử lý nhiều items

Code highlight — reverse matching (v2 fix cho lỗi "đồ bún bò Huế"):
```python
# Priority 4: reverse match — tên món nằm trong query
for key, recipe in RECIPES.items():
    recipe_words = recipe["name"].lower().split()
    if all(w in query for w in recipe_words):
        return json.dumps(recipe, ensure_ascii=False, indent=2)
```

**3. `src/chatbot.py`** — Chatbot baseline

- Class `SimpleChatbot` không có tools, dùng làm đối chứng
- Tích hợp `tracker.track_request()` để ghi `LLM_METRIC` vào log
- System prompt trung lập (không bias — ban đầu sai, đã sửa)

**4. Sửa `src/core/local_provider.py`** — Chuyển từ Phi-3 sang Qwen

Đổi từ chat template cứng của Phi-3 (`<|system|>...<|end|>`) sang `create_chat_completion()` — cho phép dùng bất kỳ GGUF model nào mà không cần sửa code.

---

## II. Case Study Debug (10 điểm)

### Case 1: System prompt bias trong chatbot

**Vấn đề**: System prompt ban đầu ghi rõ "Bạn KHÔNG có quyền truy cập database cửa hàng" → model tự từ chối ngay, trả lời "tôi không có quyền truy cập vào kho hàng". So sánh chatbot vs agent bị bias vì chatbot refuse thay vì hallucinate.

**Phát hiện**: Khi test câu "Tôi muốn nấu phở bò cho 4 người, kiểm tra nguyên liệu và tính giá", chatbot v1 từ chối hoàn toàn. Điều này không phản ánh hành vi thực tế của LLM khi không có tools — vì trong thực tế, chatbot sẽ cố trả lời và bịa.

**Cách sửa**: Đổi system prompt sang trung lập — cùng nhiệm vụ như agent nhưng không nói gì về tools hay database.

**Kết quả**:
```
Prompt v1 (bias):    "tôi không có quyền truy cập vào kho hàng" → từ chối
Prompt v2 (trung lập): "bò 15,000-30,000đ/kg" → bịa giá (thật: 280,000đ)
```

Prompt v2 cho bằng chứng mạnh hơn: chatbot tự tin trả lời nhưng sai lệch 6-10 lần so với thực tế.

**Bài học**: Thiết kế baseline phải công bằng — nếu baseline bị handicap cố ý, kết quả so sánh không có ý nghĩa.

### Case 2: Fuzzy matching quá rộng → quá hẹp → vừa đủ

**Vấn đề v1**: `search_recipe` dùng `any(w in key for w in query.split())`, nghĩa là tìm "bò" match cả "pho_bo" lẫn "bun_bo_hue" — luôn trả cái đầu tiên, không deterministic.

**Vấn đề v1 bộc lộ qua agent**: Agent gọi `search_recipe("đồ bún bò Huế")` — từ "đồ" không có trong bất kỳ recipe nào → `all()` check fail → "Không tìm thấy". Log trace:

```json
{"event": "TOOL_CALL", "data": {"tool": "search_recipe", "args": "đồ bún bò Huế"}}
{"event": "TOOL_RESULT", "data": {"result": "Không tìm thấy công thức cho 'đồ bún bò Huế'"}}
```

**Cách sửa**: Thêm 4 mức ưu tiên matching:
1. Exact match: "bún bò huế" == "Bún Bò Huế" ✓
2. Substring: "phở" in "Phở Bò" ✓
3. Multi-word: tất cả từ trong query có trong recipe ✓
4. **Reverse match (v2 mới)**: tất cả từ trong TÊN MÓN có trong query → "đồ bún bò Huế" chứa "bún", "bò", "huế" ✓

**Kết quả**: Agent tìm thấy recipe ngay bước 1 thay vì fail 3 bước rồi bỏ cuộc.

### Case 3: Tool single-item vs model multi-item

**Vấn đề v2**: `suggest_substitute` chỉ xử lý 1 nguyên liệu, nhưng model gọi `suggest_substitute("giò heo, mắm ruốc")` → chỉ match "giò heo", bỏ qua "mắm ruốc" → agent stuck loop → max_steps.

**Log evidence**:
```json
{"event": "TOOL_CALL", "data": {"tool": "suggest_substitute", "args": "giò heo, mắm ruốc"}}
{"event": "TOOL_RESULT", "data": {"result": "Thay thế cho 'giò heo': chân giò heo (đông lạnh)..."}}
// mắm ruốc bị bỏ qua → agent gọi lại → DUPLICATE_CALL → max_steps
```

**Cách sửa (v3)**: Split input bằng dấu phẩy, xử lý từng item:
```python
items = [i.strip().lower() for i in item_name.split(",") if i.strip()]
for item in items:
    # xử lý từng item
```

**Bài học**: Thiết kế tool phải phù hợp với hành vi thực tế của LLM. Model nhỏ không tuân thủ "mỗi lần 1 item" — tool phải linh hoạt thay vì ép model phải hoàn hảo.

---

## III. Nhận Xét Cá Nhân: Chatbot vs ReAct Agent (10 điểm)

### 1. Reasoning

Khác biệt cốt lõi: agent có bước **Thought** trước khi hành động. Khi nhận câu "nấu bún bò Huế, tính giá", agent suy nghĩ "cần tìm recipe trước" → gọi `search_recipe` → nhận observation → suy nghĩ "cần kiểm kho" → gọi tiếp. Mỗi bước dựa trên kết quả bước trước.

Chatbot nhận cùng câu hỏi nhưng trả lời ngay 1 lần, không có feedback loop. Nó phải "đoán" tất cả: recipe, giá, tình trạng kho — và đoán sai hệ thống (giá bò 15,000-30,000đ thay vì 280,000đ).

### 2. Reliability

Agent **tốt hơn** ở:
- Truy vấn đa bước cần data thật (giá, kho, thay thế)
- Phát hiện nguyên liệu hết hàng — chatbot không có khả năng này
- Trả lời có cơ sở (từ database) thay vì bịa

Agent **tệ hơn** ở:
- Câu đơn giản: "Phở là gì?" — agent tốn 5 bước và 97 giây, chatbot trả lời ngay 45 giây
- Chi phí token gấp 14 lần
- Đôi khi stuck loop nếu tool không xử lý input đúng (v2 bug)
- Model nhỏ (3B) đôi khi output tiếng Trung thay vì Việt

### 3. Observation feedback

Observation là yếu tố quyết định. Khi `check_inventory` trả "giò heo: HẾT HÀNG ✗", agent nhận observation này và quyết định gọi `suggest_substitute(giò heo)`. Nếu không có observation, agent sẽ giả sử mọi thứ còn hàng và trả lời sai.

Ví dụ cụ thể từ trace Bún Bò Huế:
```
Step 2 Observation: "giò heo: HẾT HÀNG ✗" + "mắm ruốc: HẾT HÀNG ✗"
Step 3 Thought: "cần tính giá trước"
Step 4 Thought: "cần gợi ý thay thế cho giò heo VÀ mắm ruốc"
→ Agent tự điều chỉnh hành vi dựa trên data thật
```

Chatbot không có feedback loop này — nó bịa rằng mọi nguyên liệu đều có sẵn.

---

## IV. Đề Xuất Cải Tiến (5 điểm)

### Mở rộng quy mô
- Thay `mock_data.py` bằng PostgreSQL/MongoDB kết nối hệ thống POS thật
- API real-time cho giá và kho hàng
- Cache layer (Redis) cho recipe search — deterministic, không cần gọi LLM lại

### Độ chính xác dữ liệu
- `calculate_price()` hiện tính theo giá đơn vị → cần mapping quantity từ recipe sang inventory (vd: "500g thịt bò" = 0.5 × 280,000đ = 140,000đ thay vì 280,000đ)
- Tính giá theo số người (nhân tỷ lệ servings)
- Giá theo mùa, combo khuyến mãi

### An toàn
- Input sanitization cho tool arguments
- Rate limiting cho API calls
- Guardrail từ chối câu hỏi không liên quan (đã thêm)
- Supervisor LLM kiểm tra output trước khi trả user

### Kiến trúc nâng cao
- Multi-agent: agent công thức + agent giá + agent kho, phối hợp bởi supervisor
- RAG: kết nối vector database chứa hàng ngàn recipe thay vì 5 recipe cố định
- Streaming response: trả từng bước cho user thay vì chờ hết flow
- Model lớn hơn (7B/14B) hoặc API (Gemini) để giảm lỗi ngôn ngữ và format
