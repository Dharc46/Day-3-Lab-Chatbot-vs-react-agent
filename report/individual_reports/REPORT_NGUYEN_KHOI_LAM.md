# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Khởi Lâm
- **Student ID**: 2A202600607
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

Phần đóng góp chính của em tập trung vào **chuẩn hóa luồng chạy project với Gemini API** (Google AI Studio) thay cho mô hình GGUF chạy local, để team có thể demo và làm lab ổn định trên máy cá nhân mà không phụ thuộc tải file ~2GB hay GPU.

### Modules đã chỉnh sửa / bổ sung

| File | Nội dung |
|------|----------|
| `app.py` | Cấu hình `get_llm()` cho `DEFAULT_PROVIDER=google`; kiểm tra định dạng key `AIza...`; tương thích Gradio 6; `demo.queue(default_concurrency_limit=1)` |
| `main.py` | Đồng bộ logic provider Gemini + validation key |
| `.env` / `.env.example` | Hướng dẫn chuyển `google` / `local` / `openai` |
| `src/core/local_provider.py` | (Phụ) Tối ưu khi fallback local: lock inference, giảm `max_tokens`, xử lý `CUDA_PATH` trên Windows |

### Code highlights

**1. Validation API key Gemini** — tránh nhầm key dạng `AQ.xxx` (gây lỗi quota `limit: 0`):

```python
api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key.startswith("AIza"):
    raise ValueError(
        "GEMINI_API_KEY phải bắt đầu bằng 'AIza' (Google AI Studio)..."
    )
return GeminiProvider(model_name=model, api_key=api_key)
```

**2. Tương thích Gradio 6** — bỏ tham số `type="messages"` (không còn trong `ChatInterface`), chuyển `theme` sang `launch()`.

**3. Đo lường hiệu năng (ước lượng thực nghiệm trên cùng câu hỏi Agent)**

| Provider | Thời gian phản hồi (1 câu, tab Agent) |
|----------|--------------------------------------|
| Local `qwen2.5-3b-instruct` (CPU) | ~90–120 giây |
| Gemini `gemini-2.5-flash-lite` | ~12–18 giây |

→ **Nhanh hơn khoảng 6–7 lần**, đủ để demo trực tiếp trước lớp mà không bị timeout UI.

### Documentation (tương tác với ReAct loop)

- `app.py` khởi tạo `ReActAgent` với `llm` từ `GeminiProvider`; mỗi bước `Thought → Action` vẫn gọi `llm.generate()` như thiết kế lab.
- Telemetry JSON trong `logs/` ghi `provider: "google"`, `latency_ms` giảm rõ so với `provider: "local"`.
- Chatbot baseline dùng cùng `llm` instance → so sánh công bằng cùng một model cloud.

---

## II. Debugging Case Study (10 Points)

### Problem Description

Khi chuyển sang Gemini, hệ thống trả về lỗi **429 Resource Exhausted** với thông báo `limit: 0` trên metric `generate_content_free_tier_requests`, dù vừa tạo API key mới. Đồng thời, lần chạy local trước đó gặp `UnicodeEncodeError` (emoji trên Windows) và crash `access violation` khi gửi hai request song song.

### Log Source (mô tả tương đương log thực tế)

```json
{
  "event": "LLM_ERROR",
  "data": {
    "error": "429 ... limit: 0, model: gemini-2.0-flash ... quota_metric: generativelanguage.googleapis.com/generate_content_free_tier_requests"
  }
}
```

### Diagnosis

1. **Key sai loại**: Key bắt đầu `AQ.Ab8...` không phải key Google AI Studio (`AIzaSy...`) → request không vào đúng bucket quota free tier.
2. **Model name / quota project**: Một số model (`gemini-2.0-flash`) báo `limit: 0` khi project chưa kích hoạt billing hoặc hết quota.
3. **Local**: `CUDA_PATH` trỏ thư mục không tồn tại → `llama_cpp` fail khi import; gửi 2 chat đồng thời → race condition trên CPU.

### Solution

| Vấn đề | Cách xử lý |
|--------|------------|
| Key / quota | Dùng key từ [Google AI Studio](https://aistudio.google.com/apikey), đặt `DEFAULT_MODEL=gemini-2.5-flash-lite`, kiểm tra https://ai.dev/rate-limit |
| Gradio | Sửa `app.py` theo API Gradio 6; `PYTHONUTF8=1` khi chạy trên PowerShell |
| Local ổn định | `threading.Lock` trong `LocalProvider`; `demo.queue(default_concurrency_limit=1)`; bỏ `CUDA_PATH` nếu path invalid |

Sau khi áp dụng, Agent hoàn thành chuỗi `search_recipe → calculate_price → Final Answer` trong vài chục giây thay vì vài phút.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning — vai trò khối `Thought`

Với **Gemini**, khối `Thought` giúp agent **lập kế hoạch tuần tự**: tra công thức trước, rồi mới tính giá. Chatbot cùng model thường trả lời **một lần**, dễ gộp nguyên liệu và giá “ước lượng” không khớp `mock_data`.

Em nhận thấy `Thought` đóng vai trò như **scratchpad**: model ghi lại giả định trước khi commit `Action`, giảm việc gọi tool sai thứ tự (ví dụ `calculate_price` trước khi biết danh sách món).

### 2. Reliability — khi Agent *kém hơn* Chatbot

- **Câu hỏi ngoài phạm vi** (thời tiết, bài tập toán): Chatbot đôi khi trả lời ngắn; Agent cố parse `Action` → hết `max_steps` → message “Xin lỗi, không hoàn thành...” (hardcode trong `agent.py`).
- **Câu đơn giản, không cần DB**: Chatbot 1 lần gọi LLM đủ dùng; Agent tốn 3–5 vòng → chậm và tốn token hơn dù Gemini đã nhanh.
- **Parse lỗi**: Model nhỏ / prompt dài dễ output không đúng `Action: tool(args)` → vòng lặp sửa format.

### 3. Observation — ảnh hưởng bước tiếp theo

`Observation` từ tool là **ground truth** trong lab: “Không tìm thấy công thức”, “HẾT HÀNG”, “TỔNG ƯỚC TÍNH: 224,000đ”. Agent bước sau buộc phải phản ứng (gọi `suggest_substitute` hoặc `Final Answer`). Chatbot **không có** feedback này nên hay hallucinate giá/nguyên liệu.

**Kết luận cá nhân**: ReAct + tools + Gemini phù hợp bài toán **có dữ liệu cửa hàng**; Chatbot phù hợp **hội thoại mở** hoặc khi không cần độ chính xác số liệu.

---

## IV. Future Improvements (5 Points)

### Scalability

- Tách **worker queue** (Redis/Celery) cho tool I/O; API Gradio chỉ enqueue job và poll kết quả.
- Cache `search_recipe` theo tên món (TTL 1h) để giảm số vòng ReAct.

### Safety

- **Supervisor LLM** kiểm tra `Action` trước khi execute (chặn tool lạ, argument injection).
- Rate limit theo user + giới hạn chi phí token/ngày trên Gemini.

### Performance

- Dùng **`google.genai` SDK mới** thay `google.generativeai` (deprecated).
- **Streaming** `Final Answer` ra UI để giảm cảm giác chờ dù TTFT vẫn phụ thuộc tool loop.
- Với nhiều tool: **RAG chọn tool** thay vì liệt kê hết trong system prompt.

### Ablation (đề xuất thí nghiệm tiếp theo)

So sánh cùng câu hỏi: `local 3B` vs `gemini-2.5-flash-lite` vs `gpt-4o-mini` — metric: latency, steps, token, tỷ lệ `PARSE_ERROR` / `DUPLICATE_CALL` trong log.

---

> **Ghi chú nộp bài**: File này đặt tại `report/individual_reports/REPORT_NGUYEN_KHOI_LAM.md` theo yêu cầu đổi tên từ template.
