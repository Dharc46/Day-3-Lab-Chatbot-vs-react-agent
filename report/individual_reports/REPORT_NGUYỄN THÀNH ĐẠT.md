# Individual Report: Lab 3 - Chatbot vs ReAct Agent

* **Student Name**: Nguyễn Thành Đạt
* **Student ID**: 2A202600944
* **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

Trong lab này, vai trò của tôi là **người C — Backend Logic**, phụ trách xây dựng phần ReAct Agent, kiểm thử kịch bản, chạy evaluation và hỗ trợ phân tích kết quả so sánh giữa Chatbot baseline và ReAct Agent.

* **Modules Implemented**:

  * `src/agent/agent.py`
  * `main.py`
  * `tests/test_scenarios.py`
  * `tests/run_tests.py`

* **Code Highlights**:

  Trong `src/agent/agent.py`, tôi hoàn thiện class `ReActAgent` theo vòng lặp ReAct:

  ```python
  result = self.llm.generate(
      current_prompt,
      system_prompt=system_prompt,
  )
  ```

  Sau mỗi lần gọi LLM, tôi thêm telemetry tracking để hệ thống ghi lại thông tin provider, model, token usage và latency:

  ```python
  tracker.track_request(
      provider=result.get("provider", "unknown"),
      model=getattr(self.llm, "model_name", "unknown"),
      usage=result.get("usage", {}),
      latency_ms=result.get("latency_ms", 0),
  )
  ```

  Tôi cũng triển khai parser để nhận diện `Final Answer`:

  ```python
  def _parse_final_answer(self, text: str) -> Optional[str]:
      match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
      if not match:
          return None

      final_answer = match.group(1).strip()
      return final_answer if final_answer else None
  ```

  Và parser để tách `Action` cùng `Action Input`:

  ```python
  def _parse_action(self, text: str) -> Optional[Dict[str, str]]:
      action_match = re.search(r"Action:\s*([a-zA-Z_]+)", text)
      input_match = re.search(r"Action Input:\s*(.*)", text)

      if not action_match or not input_match:
          return None

      return {
          "tool_name": action_match.group(1).strip(),
          "tool_input": input_match.group(1).strip(),
      }
  ```

  Phần `_execute_tool()` cho phép Agent gọi đúng tool từ `TOOL_REGISTRY` do backend data cung cấp:

  ```python
  def _execute_tool(self, tool_name: str, args: str) -> str:
      for tool in self.tools:
          if tool["name"] == tool_name:
              tool_function = tool.get("function")

              if not callable(tool_function):
                  return f"Tool {tool_name} không có function hợp lệ."

              try:
                  return tool_function(args)
              except Exception as error:
                  return f"Lỗi khi chạy tool {tool_name}: {str(error)}"

      available_tools = ", ".join([tool["name"] for tool in self.tools])
      return (
          f"Tool {tool_name} không tồn tại. "
          f"Các tool hợp lệ: {available_tools}"
      )
  ```

* **Documentation**:

  Code của tôi kết nối trực tiếp với ReAct loop bằng cách yêu cầu LLM trả về đúng một trong hai format:

  ```text
  Thought: ...
  Action: ...
  Action Input: ...
  ```

  hoặc:

  ```text
  Final Answer: ...
  ```

  Khi LLM sinh ra `Action`, Agent sẽ parse tên tool và input, sau đó gọi function tương ứng từ `TOOL_REGISTRY`. Kết quả tool được đưa lại vào prompt dưới dạng `Observation`, giúp LLM có thêm dữ liệu thật để suy luận bước tiếp theo.

  Các tool mà Agent sử dụng gồm:

  * `search_recipe`: tìm công thức món ăn.
  * `check_inventory`: kiểm tra nguyên liệu còn hay hết hàng.
  * `calculate_price`: tính tổng tiền nguyên liệu.
  * `suggest_substitute`: gợi ý nguyên liệu thay thế.

  Tôi cũng tạo `main.py` để chạy thử Agent bằng terminal, đồng thời xây dựng `tests/test_scenarios.py` và `tests/run_tests.py` để đánh giá Agent qua các tình huống simple, multi-step và edge case.

---

## II. Debugging Case Study (10 Points)

* **Problem Description**:

  Một lỗi tôi gặp trong quá trình tích hợp là khi chạy:

  ```bash
  python main.py
  ```

  chương trình báo lỗi:

  ```text
  ImportError: cannot import name 'GroceryReActAgent' from 'src.agent.agent'
  ```

  Lỗi này xảy ra vì trong `main.py` đang import class `GroceryReActAgent`, trong khi file `src/agent/agent.py` lúc đó chỉ có class tên `ReActAgent`.

* **Log Source**:

  Terminal output:

  ```text
  Traceback (most recent call last):
    File "main.py", line 4, in <module>
      from src.agent.agent import GroceryReActAgent
  ImportError: cannot import name 'GroceryReActAgent' from 'src.agent.agent'
  ```

* **Diagnosis**:

  Nguyên nhân không nằm ở LLM hoặc tool, mà là lỗi không thống nhất tên class giữa các file. File `main.py` mong đợi một class tên `GroceryReActAgent`, nhưng `agent.py` chỉ định nghĩa `ReActAgent`.

  Đây là lỗi tích hợp phổ biến khi nhiều người cùng làm trên một repo. Người C làm logic agent, người A hoặc file demo có thể import theo tên khác. Nếu không thống nhất interface, chương trình sẽ lỗi ngay từ bước import.

* **Solution**:

  Tôi sửa bằng cách thêm alias ở cuối file `src/agent/agent.py`:

  ```python
  GroceryReActAgent = ReActAgent
  ```

  Cách này giữ lại class chính là `ReActAgent`, đồng thời cho phép các file khác vẫn import bằng tên `GroceryReActAgent`.

  Ngoài ra, tôi cũng kiểm tra lại `main.py` để đảm bảo Agent được khởi tạo đúng với `TOOL_REGISTRY`:

  ```python
  agent = ReActAgent(
      llm=llm,
      tools=TOOL_REGISTRY,
      max_steps=5,
  )
  ```

  Sau khi sửa, `python main.py` có thể chạy và nhận input từ terminal.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:

   Điểm khác biệt lớn nhất giữa Chatbot thường và ReAct Agent là Agent có bước `Thought`. Với Chatbot baseline, model nhận câu hỏi và trả lời trực tiếp, nên câu trả lời phụ thuộc chủ yếu vào kiến thức ngôn ngữ của LLM. Trong khi đó, ReAct Agent phải chia vấn đề thành từng bước nhỏ hơn.

   Ví dụ với câu hỏi:

   ```text
   Tôi muốn nấu bún bò Huế, nếu thiếu nguyên liệu thì thay bằng gì và tính giá giúp tôi.
   ```

   Agent không nên trả lời ngay. Nó cần suy luận theo chuỗi:

   * Tìm công thức bún bò Huế.
   * Kiểm tra nguyên liệu có thể hết hàng.
   * Gợi ý thay thế cho nguyên liệu hết hàng.
   * Tính tổng tiền.
   * Tổng hợp câu trả lời cuối cùng.

   Nhờ có `Thought`, quá trình xử lý trở nên rõ ràng hơn và dễ debug hơn so với Chatbot thường.

2. **Reliability**:

   Agent không phải lúc nào cũng tốt hơn Chatbot. Trong các câu hỏi đơn giản như:

   ```text
   Phở bò cần nguyên liệu gì?
   ```

   Chatbot có thể trả lời nhanh hơn vì không cần nhiều bước gọi tool. Agent đôi khi chậm hơn vì phải đi qua ReAct loop, parse action, gọi tool, nhận observation rồi mới trả lời.

   Agent cũng có thể tệ hơn nếu LLM không tuân thủ format. Ví dụ, nếu model trả về:

   ```text
   Tôi sẽ tìm công thức phở bò cho bạn.
   ```

   nhưng không có `Action:` và `Action Input:`, parser sẽ không gọi được tool. Vì vậy, Agent phụ thuộc nhiều vào chất lượng prompt và khả năng model tuân thủ format.

3. **Observation**:

   `Observation` là phần giúp Agent khác biệt rõ so với Chatbot. Sau khi tool trả kết quả, Observation cung cấp dữ liệu thật từ môi trường, ví dụ công thức, trạng thái hàng còn/hết, giá tiền hoặc nguyên liệu thay thế.

   Ví dụ nếu tool `check_inventory` trả về:

   ```text
   mắm ruốc: 25,000đ/hũ — HẾT HÀNG ✗
   ```

   Agent có thể dùng Observation này để quyết định bước tiếp theo là gọi:

   ```text
   suggest_substitute
   ```

   Nhờ vậy, Agent không chỉ dựa vào suy đoán của LLM mà còn phản ứng theo dữ liệu thực tế từ hệ thống.

---

## IV. Future Improvements (5 Points)

* **Scalability**:

  Nếu mở rộng hệ thống lên production, tôi sẽ tách tool execution thành một lớp riêng như `ToolExecutor`. Khi số lượng tool tăng lên, Agent không nên duyệt list thủ công nữa mà nên dùng dictionary mapping hoặc tool registry có schema rõ ràng.

  Ngoài ra, có thể thêm async execution cho những tool mất thời gian như gọi database, API giá thị trường hoặc hệ thống tồn kho thật.

* **Safety**:

  Agent cần cơ chế kiểm soát để tránh gọi sai tool hoặc bịa dữ liệu. Một cải tiến hợp lý là thêm validation layer trước khi execute tool:

  * Kiểm tra tool name có hợp lệ không.
  * Kiểm tra input có rỗng không.
  * Kiểm tra output tool có lỗi không.
  * Nếu tool báo không tìm thấy, Agent phải trả lời không có dữ liệu thay vì tự tạo thông tin.

  Với các hệ thống nghiêm túc hơn, có thể thêm một supervisor để kiểm tra final answer trước khi gửi cho người dùng.

* **Performance**:

  ReAct Agent thường chậm hơn Chatbot vì cần nhiều lần gọi LLM. Để cải thiện, có thể:

  * Giới hạn số bước tối đa theo độ phức tạp câu hỏi.
  * Cache kết quả của các tool phổ biến như `search_recipe("phở bò")`.
  * Dùng model nhỏ hơn cho bước chọn tool, model mạnh hơn cho final answer.
  * Với nhiều tool hơn, có thể dùng vector search để chọn tool liên quan thay vì đưa toàn bộ tool description vào prompt.

* **Data Quality**:

  Hiện tại dữ liệu món ăn và giá là mock data. Trong tương lai, hệ thống nên kết nối với database thật hoặc API của siêu thị/cửa hàng để giá tiền và trạng thái tồn kho chính xác hơn.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
