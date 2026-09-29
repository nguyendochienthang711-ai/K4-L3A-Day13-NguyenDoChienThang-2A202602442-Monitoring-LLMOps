# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `high_latency_p95`
- Severity: Warning
- Duration: 5m
- Kênh thông báo: Slack (#llmops-alerts)
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (latency <= 3000ms trên 99.5% requests).
- Điều kiện và thời gian duy trì: Latency P95 vượt quá 3000ms liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Người dùng cảm nhận phản hồi từ bot rất chậm hoặc có nguy cơ bị timeout kết nối HTTP.
- Ba bước kiểm tra đầu tiên:
  1. Mở Dashboard Panel `Latency` để kiểm tra TTFT (Time to First Token) và phân vị P50/P95/P99 xem độ trễ tăng đột biến ở toàn bộ hay chỉ một nhóm query.
  2. Lọc log trong `data/logs.jsonl` tìm các event `response_sent` có `latency_ms > 3000`, trích xuất `correlation_id` của các request bị chậm.
  3. Tra cứu `correlation_id` trên Langfuse trace waterfall để xác định span chậm: do span `retrieval` (vector database/RAG quá tải) hay do span `llm-generation` (mô hình phản hồi chậm).
- Mitigation tạm thời:
  1. Nếu span `retrieval` bị chậm: giảm timeout retrieval, bật cache kết quả tìm kiếm hoặc chuyển sang chế độ fallback context ngắn.
  2. Nếu span `llm-generation` bị chậm: kiểm tra trạng thái API provider, kích hoạt fallback model hoặc giảm `max_tokens`.
- Owner: oncall-llmops

## Alert 2

- Tên: `high_error_rate`
- Severity: Critical
- Duration: 3m
- Kênh thông báo: Slack (#llmops-critical)
- SLI/SLO liên quan: Guardrail `error_rate_pct_max: 2` (tỉ lệ lỗi HTTP 500 không vượt quá 2%).
- Điều kiện và thời gian duy trì: Tỉ lệ lỗi `request_failed` / `request_received` > 2% liên tục trong 3 phút.
- Ảnh hưởng tới người dùng: Người dùng nhận thông báo lỗi hệ thống "Internal Server Error" và không nhận được câu trả lời từ trợ lý AI.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard Panel `Errors` xem `error_type` chính đang xảy ra (ví dụ: `RuntimeError`, `RateLimitError`, `TimeoutException`).
  2. Lọc log `data/logs.jsonl` với `event == "request_failed"` để xem stack trace và payload detail kèm `correlation_id`.
  3. Mở trace trên Langfuse ứng với `correlation_id` lỗi để xác định thành phần ném ngoại lệ (retrieval vector DB hay LLM generation).
- Mitigation tạm thời:
  1. Nếu vector DB bị lỗi kết nối (`RuntimeError: Vector store timeout`): kích hoạt cờ bypass RAG để bot trả lời fallback dựa trên kiến thức nền tạm thời.
  2. Nếu do downstream service crash: khởi động lại service pod hoặc chuyển hướng traffic sang backup replica.
- Owner: oncall-llmops

## Alert 3

- Tên: `low_quality_score`
- Severity: Warning
- Duration: 10m
- Kênh thông báo: Slack (#llmops-alerts)
- SLI/SLO liên quan: Guardrail `quality_score_avg_min: 0.75` và `retrieval_success_rate_pct_min: 90`.
- Điều kiện và thời gian duy trì: Điểm chất lượng trung bình (`mean(quality_score)`) giảm xuống dưới 0.75 trong cửa sổ 10 phút.
- Ảnh hưởng tới người dùng: Câu trả lời của bot không liên quan đến câu hỏi, thiếu ngữ cảnh tài liệu hoặc chứa nhiều nội dung fallback chất lượng kém.
- Ba bước kiểm tra đầu tiên:
  1. Xem Dashboard Panel `Quality proxy` và Panel `Errors` (mục retrieval success rate) để đối chiếu xu hướng suy giảm.
  2. Lọc các log `response_sent` có `quality_score < 0.75` trong `data/logs.jsonl`, xem `feature` và `prompt_version` đang chạy.
  3. Kiểm tra trace trên Langfuse để xem prompt template có bị thay đổi gần đây (prompt release mới) hoặc document corpus có bị rỗng/thiếu thông tin không.
- Mitigation tạm thời:
  1. Nếu nguyên nhân do prompt version mới vừa triển khai: thực hiện ngay thao tác rollback prompt label `production` về phiên bản ổn định trước đó (v1) trên Langfuse.
  2. Nếu do dữ liệu tài liệu RAG bị lỗi index: re-index corpus hoặc bổ sung fallback response phù hợp.
- Owner: oncall-llmops

