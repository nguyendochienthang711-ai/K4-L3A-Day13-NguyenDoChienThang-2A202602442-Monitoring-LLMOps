# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Đỗ Chiến Thắng
- **MSSV:** 2A202602442
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/nguyendochienthang711-ai/K4-L3A-Day13-NguyenDoChienThang-2A202602442-Monitoring-LLMOps
- **Commit SHA cuối:** `df2de82c8a4a60ebca1cb82de61df9a4de045a91`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602442`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt toàn bộ schema, correlation ID propagation, enrichment và PII scrubbing |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Đầy đủ 6 panel theo đúng contract |
| `pytest` | 22 passed | 22 passed | Toàn bộ unit tests & integration tests đều vượt qua |
| Số traces hợp lệ | 0 | 20 traces | Đã tạo và đồng bộ 20 traces lên project Langfuse cá nhân |
| Số PII leak | 0 | 0 | Không còn rò rỉ email, số điện thoại, CCCD hay số thẻ tín dụng |
| Latency P95 / TTFT P95 | 170.5ms / 50ms | 170.9ms / 50ms | Đo đạc thực tế trên 10 sample queries baseline |
| Retrieval success rate | 100% | 100% | 10/10 request đều retrieve thành công tài liệu liên quan |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  - Sử dụng `CorrelationIdMiddleware` kế thừa từ `BaseHTTPMiddleware` của FastAPI/Starlette.
  - Trước khi xử lý mỗi request, middleware gọi `clear_contextvars()` để xóa toàn bộ context cũ, tránh rò rỉ dữ liệu giữa các request bất đồng bộ.
  - Middleware kiểm tra header `x-request-id`: nếu có giá trị thì sử dụng, nếu không có hoặc rỗng thì sinh mã ngẫu nhiên theo đúng chuẩn `req-<8-hex>` thông qua `f"req-{uuid.uuid4().hex[:8]}"`.
  - Giá trị correlation ID được bind vào structlog contextvars (`bind_contextvars(correlation_id=correlation_id)`) và gán vào `request.state.correlation_id`.
  - Sau khi downstream xử lý xong, middleware đo lường thời gian xử lý và gắn trả `x-request-id` cùng `x-response-time-ms` vào response headers.

- **Các metadata được ghi vào structured log:**
  - Tại endpoint `/chat`, trước khi ghi log `request_received`, gọi `bind_contextvars` để làm giàu context với:
    + `user_id_hash`: SHA-256 (12 ký tự đầu) của `user_id` để ẩn danh người dùng.
    + `session_id`: mã định danh phiên hội thoại của người dùng.
    + `feature`: tính năng được gọi (ví dụ `qa`, `summary`).
    + `model`: tên mô hình đang sử dụng (`claude-sonnet-4-5`).
    + `env`: môi trường triển khai (`dev`, `prod`).
  - Các log `response_sent` bổ sung: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, và `answer_preview`.

- **Cách bảo đảm PII được scrub trước khi ghi:**
  - Định nghĩa hàm xử lý `scrub_event` trong `app/logging_config.py` và đăng ký nó trong chuỗi pipeline `structlog.configure(processors=[...])` trước các bước ghi file (`JsonlFileProcessor`) và render (`JSONRenderer`).
  - `scrub_event` áp dụng thuật toán đệ quy duyệt qua toàn bộ dictionary/list/string trong `event_dict`, gọi `scrub_text` đối với mọi trường dạng chuỗi để che hoàn toàn:
    + Email: `[REDACTED_EMAIL]`
    + Số điện thoại Việt Nam (+84 hoặc 0x): `[REDACTED_PHONE_VN]`
    + Số CCCD (12 chữ số): `[REDACTED_CCCD]`
    + Số thẻ tín dụng: `[REDACTED_CREDIT_CARD]`
    + Hộ chiếu: `[REDACTED_PASSPORT]`

- **Cách kiểm chứng kết quả:**
  - Chạy `scripts/load_test.py` với các câu hỏi mẫu chứa dữ liệu nhạy cảm thật trong `data/sample_queries.jsonl` (email `@vinuni.edu.vn`, số điện thoại `0987654321`, thẻ `4111 1111 1111 1111`).
  - Chạy `python scripts/validate_logs.py` kiểm tra độc lập toàn bộ `data/logs.jsonl`. Kết quả đạt 100/100, xác nhận 0 rò rỉ PII và 10/10 correlation IDs duy nhất.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  - Tạo project riêng trên Langfuse Cloud: `day13-k4-l3a-2A202602442`.
  - Cấu hình `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` cá nhân vào file `.env`.
  - Mọi trace tạo ra đều mang tag `["lab", feature, self.model]`, trace name `day13-agent-request`, user_id dạng hash và chứa metadata `correlation_id` khớp với correlation ID trong log.

- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `@observe(name="lab-agent-run", as_type="agent")` bao quát toàn bộ quy trình thực thi của Agent.
  - Child observation 1: `@observe(name="retrieval", as_type="retriever")` đo lường thời gian và kết quả tìm kiếm ngữ cảnh từ kho tài liệu RAG (`retrieve`).
  - Child observation 2: `@observe(name="llm-generation", as_type="generation")` đo lường bước gọi mô hình ngôn ngữ (`FakeLLM.generate`), cập nhật thông tin `model`, `prompt`, `usage_details` (input/output tokens) và `cost_details` (chi phí USD ước tính) thông qua `update_current_generation`.

- **Cách nối trace với log:**
  - Trong log của API, mỗi request đều có trường `correlation_id: "req-<8-hex>"`.
  - Khi bắt đầu trace, hàm `run` truyền `correlation_id` vào trace metadata thông qua `propagate_attributes(metadata={"correlation_id": correlation_id, ...})`.
  - Khi cần điều tra một request từ log, ta chỉ cần copy `correlation_id` và tìm kiếm trên Langfuse để mở đúng trace tương ứng.

- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (label `baseline`)
- **Version/label candidate:** Version 2 (label `candidate`, `production`)
- **Trace ID của mỗi version:**
  - Trace ID baseline (v1): `c55537e95b8628a23b8be0d2ed8c8a39`
  - Trace ID candidate (v2): `907cb8de21926d638a7aff65db0a3297`
- **Cách promote và rollback `production`:**
  - Promote: Trên giao diện Langfuse Prompt Management, chuyển label `production` từ v1 sang v2. Khi API khởi động lại với `LANGFUSE_PROMPT_LABEL=production`, nó sẽ tự động lấy v2.
  - Rollback: Khi phát hiện sự cố ở v2, chuyển label `production` quay lại trỏ về v1 trên Langfuse. Ứng dụng lập tức sử dụng lại v1 mà không cần sửa đổi bất kỳ dòng mã nguồn nào.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  - Định nghĩa theo contract chuẩn trong `config/dashboard.yaml` với nguồn dữ liệu từ `data/logs.jsonl`:
    1. `latency`: Percentile P50, P95, P99 của `latency_ms` và `ttft_ms` P95 (threshold: P95 <= 3000ms).
    2. `traffic`: Tổng số request và tốc độ request/phút theo dõi tải hệ thống.
    3. `errors`: Tỉ lệ lỗi tổng thể (`request_failed / request_received`) và tỉ lệ retrieval thành công (`tool_success`).
    4. `cost`: Tổng chi phí USD theo từng phút và tích lũy toàn cửa sổ 60 phút.
    5. `tokens`: Tổng lượng input tokens và output tokens tiêu thụ.
    6. `quality`: Điểm chất lượng trung bình của câu trả lời (`mean(quality_score)`).

- **SLO và lý do chọn:**
  - Primary SLO: `fast_successful_requests` với mục tiêu 99.5% requests hoàn thành thành công và có độ trễ <= 3000ms trong cửa sổ 28 ngày (`28d`).
  - Lý do chọn: Trong ứng dụng AI Chatbot hỗ trợ người dùng, độ trễ trên 3 giây bắt đầu gây ức chế và làm giảm tương tác của người dùng. Ngưỡng 3000ms bảo đảm trải nghiệm mượt mà trong khi vẫn cho phép mô hình thực hiện retrieval và generation.

- **Cách tính error budget:**
  - Với mục tiêu SLO = 99.5%, Error Budget cho phép là $100\% - 99.5\% = 0.5\%$.
  - Trong cửa sổ 28 ngày, nếu có tổng cộng 1,000,000 requests, hệ thống được phép có tối đa $1,000,000 \times 0.5\% = 5,000$ requests bị chậm (> 3000ms) hoặc bị lỗi (HTTP 500).

- **Ba alert và runbook tương ứng:**
  - Cấu hình trong `config/alert_rules.yaml` và chi tiết runbook tại `docs/alerts.md`:
    1. `high_latency_p95`: Severity `warning`, kích hoạt khi Latency P95 > 3000ms liên tục trong 5 phút. Runbook hướng dẫn kiểm tra TTFT, xác định span nghẽn (retrieval vs llm) qua Langfuse và bật cache/short-context fallback.
    2. `high_error_rate`: Severity `critical`, kích hoạt khi Error Rate > 2% liên tục trong 3 phút. Runbook hướng dẫn tra cứu log `request_failed` tìm stack trace lỗi và bật cờ bypass retrieval nếu vector DB timeout.
    3. `low_quality_score`: Severity `warning`, kích hoạt khi điểm chất lượng trung bình < 0.75 trong 10 phút. Runbook hướng dẫn đối chiếu retrieval success rate và thực hiện rollback prompt về version ổn định trước đó.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-29 11:14:40 UTC đến 11:15:00 UTC (18:14:40 đến 18:15:00 giờ địa phương)
- **Triệu chứng từ metrics:**
  - Độ trễ phản hồi của hệ thống tăng vọt từ mức bình thường (~170ms) lên trên 3,300ms (thời gian client ghi nhận lên tới 10,068ms - 15,964ms khi chịu tải đồng thời), vi phạm nghiêm trọng ngưỡng SLO 3,000ms và ngưỡng cảnh báo của challenge `latency_threshold_ms: 2000`.
  - Triệu chứng tập trung tại tính năng `feature: monitoring`.
- **Log line và correlation ID liên quan:**
  - Correlation ID: `req-d7398858`
  - Request log: `{"service": "api", "payload": {"message_preview": "How should an engineer investigate tail latency?"}, "event": "request_received", "user_id_hash": "aae0b94055a9", "correlation_id": "req-d7398858", "env": "dev", "feature": "monitoring", "model": "claude-sonnet-4-5", "session_id": "k4-l3a-challenge-s02", "level": "info", "ts": "2026-09-29T11:14:41.274170Z"}`
  - Response log: `{"service": "api", "latency_ms": 3378, "ttft_ms": 50, "tokens_in": 34, "tokens_out": 169, "cost_usd": 0.002637, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer..."}, "event": "response_sent", "user_id_hash": "aae0b94055a9", "correlation_id": "req-d7398858", "env": "dev", "feature": "monitoring", "model": "claude-sonnet-4-5", "session_id": "k4-l3a-challenge-s02", "level": "info", "ts": "2026-09-29T11:14:44.736360Z"}`
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID trên Langfuse: `07a36fdbf3d0c3d5ab990a7ebafabe71`
  - Phân rã thời gian qua các span con:
    + Root span `lab-agent-run` (Agent): 3.379 giây
    + Span `retrieval` (Retriever): **2.501 giây** (từ 11:14:41.358Z đến 11:14:43.859Z)
    + Span `llm-generation` (Generation): 0.152 giây (từ 11:14:44.584Z đến 11:14:44.736Z)
  - Span trực tiếp gây ra độ trễ cao là **`retrieval`**.
- **Root cause:**
  - Thành phần tìm kiếm tài liệu (vector store retrieval) của tính năng `monitoring` gặp sự cố suy giảm hiệu năng nghiêm trọng (mô phỏng bởi sự cố `rag_slow`), mất tới 2.501s để hoàn thành việc truy xuất tài liệu (chiếm hơn 74% tổng thời gian request). Trong khi đó, mô hình LLM vẫn phản hồi nhanh chóng trong 152ms.
- **Fix action:**
  - Bổ sung cơ chế caching kết quả tìm kiếm ngữ cảnh cho các câu hỏi phổ biến thuộc feature `monitoring` để giảm tải trực tiếp cho vector store.
  - Cấu hình timeout chặt chẽ cho thao tác retrieval (ví dụ: tối đa 1,500ms) kèm theo fallback trả lời trực tiếp từ tri thức mô hình nếu retrieval quá hạn.
  - Tắt tình trạng nghẽn vector store bằng cách vô hiệu hóa incident: `python scripts/inject_incident.py --disable`.
- **Preventive measure:**
  - Giám sát độ trễ riêng biệt của span retrieval trên Langfuse/Dashboard để phát hiện sớm hiện tượng nghẽn vector DB trước khi ảnh hưởng đến toàn bộ request latency.
  - Áp dụng mẫu thiết kế Circuit Breaker: nếu vector store có dấu hiệu chậm liên tục trong 1 phút, tự động chuyển sang chế độ degraded mode để duy trì độ trễ < 1 giây cho người dùng.
  - Duy trì alert `high_latency_p95` với kênh thông báo Slack để đội oncall can thiệp ngay lập tức.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  - Đăng ký bộ lọc PII `scrub_event` dưới dạng processor duyệt đệ quy ở tầng structlog trước bước `JsonlFileProcessor` và `JSONRenderer`.
  - Lý do: Đảm bảo dữ liệu nhạy cảm của người dùng (email, số điện thoại, CCCD, thẻ ngân hàng) được làm sạch triệt để ở tất cả các cấp dữ liệu (payload, metadata, log message) trước khi dữ liệu được ghi xuống đĩa hoặc truyền qua mạng, ngăn chặn hoàn toàn rủi ro vi phạm bảo mật dữ liệu cá nhân (GDPR/Nghị định 13).

- **Một lỗi/blocker đã gặp:**
  - Khi cài đặt các gói phụ thuộc trên môi trường Windows với Python 3.14, gói `pydantic-core==2.11.4` trong `requirements.txt` không có wheel binary tương thích nên hệ thống cố gắng compile bằng Cargo/Rust và bị lỗi thiếu `link.exe` (MSVC C++ Build Tools).

- **Cách tìm nguyên nhân và xử lý:**
  - Phân tích log lỗi từ pip subprocess, nhận diện nguyên nhân do thiếu MSVC linker khi build mã nguồn C/Rust trên Python 3.14.
  - Xử lý bằng cách sử dụng phiên bản `pydantic 2.13.4` và `pydantic_core 2.46.4` đã có sẵn wheel pre-built trong môi trường, sau đó cài đặt thành công các thư viện còn lại (`fastapi`, `uvicorn`, `structlog`, `langfuse`, `PyYAML`, `pytest`) mà không cần compile.

- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics** là tầng quan sát cấp cao (vĩ mô), cung cấp cái nhìn tổng quan về "sức khỏe" hệ thống (P95 latency tăng vọt, Error rate vượt ngưỡng, Traffic biến động) giúp phát hiện triệu chứng và khoanh vùng thời gian xảy ra sự cố.
  - **Logs** là tầng trung gian chi tiết (vi mô theo sự kiện), sử dụng bộ lọc thời gian và sự kiện lỗi để tìm ra chính xác request bị ảnh hưởng kèm theo định danh duy nhất `correlation_id`.
  - **Traces** là tầng phân tích sâu (nội soi bên trong), dùng `correlation_id` để tra cứu cây thực thi phân tán (waterfall), phân rã thời gian xử lý qua từng span con (`retrieval` vs `llm-generation`) để xác định chính xác thành phần gây lỗi hoặc làm chậm hệ thống (Root Cause).

- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - **Prompt version & Rollback:** Cho phép kiểm soát các phiên bản prompt như mã nguồn phần mềm, gán nhãn (`production`, `candidate`) để tách biệt việc thử nghiệm với vận hành thực tế. Khi prompt mới gây suy giảm chất lượng hoặc tăng đột biến chi phí, ta có thể rollback ngay lập tức mà không cần deploy lại code.
  - **Token & Cost monitoring:** Giúp kiểm soát chi phí gọi LLM theo thời gian thực, phát hiện sớm các hiện tượng prompt injection hoặc response lặp vô tận gây cạn kiệt ngân sách.
  - **SLO & Error Budget:** Đặt ra ranh giới rõ ràng giữa tốc độ phát triển tính năng mới và độ ổn định của hệ thống, giúp đội ngũ đưa ra quyết định khách quan khi nào cần dừng deploy để củng cố hệ thống.

- **Điều quan trọng nhất đã học:**
  - Xây dựng hệ thống quan sát (observability) chuẩn chỉnh cho ứng dụng LLM không chỉ đơn giản là in log ra console, mà cần có cấu trúc log JSON nhất quán, cơ chế ẩn danh PII tự động, và sự liên kết chặt chẽ giữa Metrics, Logs và Traces qua Correlation ID.

- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  - Hệ thống đã hoàn thiện 100% mã nguồn và các yêu cầu kỹ thuật của bài lab, vượt qua toàn bộ các bài kiểm tra `validate_logs.py` (100/100), `validate_dashboard.py` (6/6 panel) và `pytest` (22/22 passed). Một điểm hạn chế là bài lab sử dụng `FakeLLM` để mô phỏng phản hồi nhằm tiết kiệm chi phí API, tuy nhiên kiến trúc quan sát phân tán theo luồng Metrics → Logs → Traces và cơ chế quản lý vòng đời Prompt Versioning trên Langfuse Cloud đã được tích hợp và hoạt động hoàn chỉnh theo đúng chuẩn môi trường production thực tế.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
