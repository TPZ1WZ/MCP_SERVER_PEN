# Tổng kết giai đoạn 1: Xây dựng nền tảng Manufacturing MCP Lab

Ngày ghi nhận: 05/10/2026.

Tài liệu mô tả các thành phần đã được triển khai trong mã nguồn của dự án. Đây là bản tổng kết dựa trên việc đọc mã và bộ kiểm thử hiện có, không phải biên bản xác nhận toàn bộ hệ thống đã chạy thành công. Khi lập tài liệu, không chạy lại các bài test vì chúng tạo lại cơ sở dữ liệu.

## 1. Mục tiêu giai đoạn 1

Giai đoạn 1 xây dựng môi trường mô phỏng vận hành nhà máy, có dữ liệu PostgreSQL và MCP Server để chuẩn bị kết nối AI Agent ở giai đoạn 2.

Nền tảng này phục vụ hai mục đích:

- Cung cấp các thao tác tra cứu, bảo trì và thay đổi cấu hình máy qua công cụ MCP.
- Tạo hai chế độ `secure` và `vulnerable` để so sánh hành vi kiểm soát truy cập, kiểm tra đầu vào và phê duyệt trong bài lab bảo mật.

Các thao tác hiện tại đọc và cập nhật dữ liệu mô phỏng trong PostgreSQL; chưa có thành phần kết nối điều khiển thiết bị vật lý.

## 2. Kiến trúc đã xây dựng

```text
MCP Client / AI Agent (dự kiến ở giai đoạn 2)
                     |
                 MCP qua stdio
                     |
             mcp_server/server.py
                /           \
     security.py             audit.py
  Kiểm tra chính sách       Ghi nhật ký
                |
        database/models.py
                |
      database/connection.py
                |
             PostgreSQL

Resource tài liệu SOP:
manual://fault-handling → mcp_server/data/fault_handling.txt
```

MCP Server là lớp tiếp nhận lệnh có cấu trúc từ client. Lớp bảo mật kiểm tra yêu cầu trước khi lớp dữ liệu thực hiện thao tác; nhật ký ghi lại các quyết định cho phép hoặc từ chối đã được xử lý.

## 3. Những phần đã thực hiện

### 3.1. Môi trường và cơ sở dữ liệu

Các file liên quan: [docker-compose.yml](../docker-compose.yml), [requirements.txt](../requirements.txt), [database/config.py](../database/config.py), [database/connection.py](../database/connection.py).

- Khai báo PostgreSQL bằng Docker Compose, sử dụng image `postgres:16-alpine`.
- Ánh xạ cổng máy chủ `5433` tới cổng PostgreSQL `5432` trong container.
- Có volume lưu dữ liệu và healthcheck kiểm tra PostgreSQL.
- Cho phép cấu hình kết nối bằng các biến môi trường `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- Sử dụng connection pool với số kết nối từ 1 đến 10.
- Khai báo các thư viện Python phục vụ MCP, PostgreSQL và pytest.

**Ý nghĩa:** tạo môi trường dữ liệu dùng chung cho các công cụ và các kịch bản thử nghiệm.

### 3.2. Mô hình dữ liệu và dữ liệu mẫu

[database/init_db.py](../database/init_db.py) triển khai việc tạo lại 5 bảng và nạp dữ liệu mẫu:

| Bảng | Nội dung | Số bản ghi mẫu trong script |
|---|---|---:|
| `users` | Người dùng, vai trò, dây chuyền được phân công | 6 |
| `machines` | Máy, trạng thái, nhiệt độ, tốc độ, ngưỡng nhiệt | 3 |
| `quality_records` | Lô sản xuất, tỷ lệ đạt và tỷ lệ lỗi | 5 |
| `maintenance_tickets` | Phiếu bảo trì, nội dung sự cố, trạng thái, người tạo | 7 |
| `configuration_changes` | Yêu cầu đổi cấu hình, giá trị cũ/mới, người đề xuất/duyệt | 7 |

Dữ liệu mô phỏng có hai dây chuyền `LINE-A`, `LINE-B` và ba vai trò `operator`, `maintenance_engineer`, `supervisor`. Máy `M-002` có trạng thái `FAULT` và nhiệt độ mẫu 95,2°C để phục vụ tình huống sự cố.

[database/reset_db.py](../database/reset_db.py) gọi lại hàm khởi tạo để đưa dữ liệu về bộ mẫu. Cả khởi tạo và reset đều xóa các bảng hiện có rồi tạo lại; các con số trên mô tả dữ liệu seed, không xác nhận số bản ghi trong database đang chạy.

**Ý nghĩa:** có dữ liệu tái lập để thử quyền theo vai trò, truy cập khác dây chuyền và thay đổi trạng thái nghiệp vụ.

### 3.3. Lớp thao tác dữ liệu

[database/models.py](../database/models.py) đã có các hàm:

- Tra cứu người dùng, máy và chất lượng lô sản xuất.
- Tạo phiếu bảo trì với trạng thái `OPEN`.
- Liệt kê phiếu bảo trì, tùy chọn lọc theo máy.
- Tạo và tra cứu yêu cầu thay đổi cấu hình.
- Phê duyệt yêu cầu đang chờ và cập nhật thông số máy.

Khi phê duyệt, mã dùng `SELECT ... FOR UPDATE` để khóa bản ghi yêu cầu trong giao dịch, kiểm tra trạng thái `PENDING_APPROVAL`, rồi cập nhật máy và yêu cầu.

**Ý nghĩa:** tách thao tác PostgreSQL khỏi phần giao tiếp MCP và chính sách bảo mật.

### 3.4. MCP Server và các công cụ nghiệp vụ

[mcp_server/server.py](../mcp_server/server.py) khởi tạo `FastMCP` với tên `Manufacturing Operations Server`, chạy bằng transport `stdio`. Log vận hành được chuyển sang `stderr` để tránh trộn vào luồng giao thức trên `stdout`.

Server đã đăng ký 6 công cụ:

| Công cụ | Chức năng |
|---|---|
| `get_machine_status` | Tra cứu trạng thái và thông số máy |
| `get_quality_record` | Tra cứu tỷ lệ đạt, tỷ lệ lỗi của lô sản xuất |
| `create_maintenance_ticket` | Tạo phiếu yêu cầu bảo trì |
| `get_maintenance_tickets` | Xem phiếu bảo trì, có thể lọc theo máy |
| `request_configuration_change` | Đề xuất đổi `speed` hoặc `temperature_threshold` |
| `approve_configuration_change` | Duyệt yêu cầu đang chờ và cập nhật máy |

Kết quả trả về có trường `success` cùng dữ liệu nghiệp vụ hoặc thông báo lỗi.

**Ý nghĩa:** cung cấp giao diện để client và AI Agent có thể gọi các chức năng nhà máy mà không cần tự viết truy vấn database.

### 3.5. Kiểm soát quyền và đầu vào

[mcp_server/security.py](../mcp_server/security.py) triển khai kiểm tra người dùng tồn tại, quyền theo vai trò, phạm vi dây chuyền và dữ liệu đầu vào. Chính sách được khai báo trong [database/config.py](../database/config.py).

Ma trận quyền trong chế độ `secure`:

| Công cụ | Operator | Maintenance engineer | Supervisor |
|---|---|---|---|
| Xem trạng thái máy | Có | Có | Có |
| Xem chất lượng lô | Không | Có | Có |
| Tạo phiếu bảo trì | Không | Có | Có |
| Xem phiếu bảo trì | Không | Có | Có |
| Đề xuất đổi cấu hình | Không | Không | Có |
| Duyệt đổi cấu hình | Không | Không | Có |

Quy tắc phạm vi kiểm tra dây chuyền được phân công với dây chuyền của máy hoặc lô hàng. Trong mã hiện tại, supervisor hoặc người dùng có `assigned_line=None` được bỏ qua giới hạn dây chuyền.

Các ràng buộc đầu vào đã có:

- Chỉ cho phép đổi `speed` và `temperature_threshold`.
- Tốc độ nằm trong khoảng 0–3.000 RPM.
- Ngưỡng nhiệt độ nằm trong khoảng 50–120°C.
- Mô tả sự cố dài 5–500 ký tự sau khi loại bỏ khoảng trắng hai đầu để kiểm tra.

**Ý nghĩa:** thực thi chính sách ở phía server, thay vì chỉ trông chờ AI tuân thủ hướng dẫn bằng văn bản.

### 3.6. Hai chế độ phục vụ bài lab

Biến môi trường `LAB_MODE` quyết định chế độ, mặc định là `secure`.

| Hành vi | `secure` | `vulnerable` |
|---|---|---|
| Kiểm tra người dùng tồn tại | Có | Có |
| Kiểm tra vai trò | Có | Bỏ qua |
| Kiểm tra phạm vi dây chuyền | Có, tại nơi gọi hàm kiểm tra | Bỏ qua |
| Kiểm tra allowlist và khoảng giá trị tại lớp security | Có | Bỏ qua |
| Kiểm tra mô tả sự cố tại lớp security | Có | Bỏ qua |
| Đề xuất đổi cấu hình | Lưu `PENDING_APPROVAL` | Lưu `APPROVED` và áp dụng ngay |
| File nhật ký | `logs/audit_secure.log` | `logs/audit_vulnerable.log` |

Bỏ qua kiểm tra ở lớp security không có nghĩa mọi đầu vào đều thực thi được: kiểu tham số, chuyển đổi dữ liệu và ràng buộc database vẫn có thể gây lỗi.

**Ý nghĩa:** dùng cùng bộ chức năng để quan sát tác động khi các lớp kiểm soát bị vô hiệu hóa.

### 3.7. Nhật ký kiểm toán

[mcp_server/audit.py](../mcp_server/audit.py) ghi JSON theo từng dòng, mở file ở chế độ ghi nối tiếp. Mỗi bản ghi gồm thời gian UTC, người gọi, vai trò, tên công cụ, tham số, tài nguyên, quyết định `ALLOW`/`DENY`, kết quả, trạng thái thành công và chế độ lab.

**Ý nghĩa:** có bằng chứng để phân tích các thao tác được chấp nhận hoặc bị từ chối giữa hai chế độ. Việc ghi nối tiếp hiện tại chưa phải cơ chế chống sửa hoặc xóa log.

### 3.8. Tài liệu nghiệp vụ qua MCP Resource

Resource `manual://fault-handling` đọc file [mcp_server/data/fault_handling.txt](../mcp_server/data/fault_handling.txt), gồm hướng dẫn xử lý quá nhiệt, điều chỉnh tốc độ và phân quyền dây chuyền.

Đây là nội dung hướng dẫn để client đọc; server không tự giám sát nhiệt độ, tự tạo phiếu hay tự dừng máy theo tài liệu này. Bản `data/fault_handling.txt` ở thư mục gốc không phải đường dẫn resource đang đọc.

**Ý nghĩa:** chuẩn bị nguồn ngữ cảnh nghiệp vụ cho AI Agent và tình huống indirect prompt injection trong giai đoạn sau.

### 3.9. Bộ kiểm thử hiện có

[tests/test_lab.py](../tests/test_lab.py) có 6 bài test gọi trực tiếp các hàm trong server, với kỳ vọng thay đổi theo `LAB_MODE`:

| Tình huống | Kỳ vọng `secure` | Kỳ vọng `vulnerable` |
|---|---|---|
| Operator xem máy cùng dây chuyền | Thành công | Thành công |
| Operator xem máy khác dây chuyền | Từ chối | Thành công |
| Operator tạo phiếu bảo trì | Từ chối | Thành công |
| Supervisor đề xuất đổi tốc độ | Chờ duyệt | Áp dụng ngay |
| Operator duyệt yêu cầu cấu hình | Từ chối | Thành công |
| Đề xuất tốc độ 99.999 RPM | Từ chối | Thành công |

Fixture tự gọi `init_db()` trước mỗi bài test. Các test này phụ thuộc PostgreSQL và sẽ xóa, tạo lại dữ liệu bảng; chúng chưa kiểm tra giao tiếp MCP qua `stdio` hoặc luồng AI Agent hoàn chỉnh. Tài liệu này ghi nhận bộ test đã được viết, không khẳng định kết quả chạy mới.

## 4. Ví dụ luồng nghiệp vụ đã triển khai

Trong chế độ `secure`, với dữ liệu mẫu:

1. Client gọi `request_configuration_change` với `actor_id="u_sup1"`, `machine_id="M-001"`, `setting="speed"`, `new_value=2000`.
2. Server kiểm tra người dùng, vai trò, phạm vi và khoảng giá trị.
3. Database lưu yêu cầu `PENDING_APPROVAL`; thông số máy chưa được cập nhật bởi yêu cầu này.
4. Client gọi `approve_configuration_change` bằng một tài khoản supervisor và mã yêu cầu vừa nhận.
5. Database kiểm tra yêu cầu còn chờ, cập nhật tốc độ máy và chuyển yêu cầu sang `APPROVED`.
6. Các nhánh thành công ghi nhật ký `ALLOW`; lỗi chính sách được xử lý bằng `SecurityError` ghi `DENY`.

Trong chế độ `vulnerable`, bước đề xuất tự cập nhật máy và lưu yêu cầu đã duyệt, không cần một lần gọi phê duyệt riêng.

## 5. Những giới hạn còn tồn tại trong giai đoạn 1

Các điểm sau giúp xác định đúng phạm vi đã hoàn thành:

- **Chưa xác thực danh tính người gọi:** `actor_id` được truyền vào công cụ và kiểm tra có tồn tại trong database, chưa được ràng buộc với phiên đăng nhập hoặc thông tin xác thực đáng tin cậy.
- **Chưa bảo đảm hai người riêng biệt:** SOP yêu cầu hai người tham gia, nhưng mã duyệt chưa kiểm tra người duyệt khác người đề xuất. Cùng một supervisor vẫn có thể đề xuất và duyệt.
- **Chưa lọc phạm vi khi lấy toàn bộ phiếu bảo trì:** `get_maintenance_tickets` chỉ kiểm tra phạm vi máy khi có `machine_id`. Nếu bỏ tham số này, người có quyền gọi công cụ nhận danh sách toàn bộ phiếu.
- **Audit chưa bao phủ mọi lỗi:** các nhánh thành công và `SecurityError` có ghi audit, nhưng nhánh lỗi nội bộ tổng quát chỉ ghi log lỗi. Lỗi ghi audit cũng không làm thao tác nghiệp vụ thất bại.
- **Tài liệu SOP chưa phải tự động hóa:** các hành động như dừng máy hoặc tạo phiếu khi quá nhiệt mới là hướng dẫn, chưa có tiến trình thực hiện tự động.
- **Chưa có kiểm thử đầy đủ:** bộ test hiện tại chưa bao phủ toàn bộ công cụ, biên giá trị, resource, lỗi database hoặc giao thức MCP.
- **Chưa có tích hợp AI Agent:** thư mục `llm_agent` hiện có file package và README mô tả kế hoạch giai đoạn 2, chưa có client hoặc vòng lặp agent.

Do đó, `secure` là tên chế độ kiểm soát của bài lab, chưa phải kết luận hệ thống đã sẵn sàng vận hành thực tế.

## 6. Phần việc chuyển sang giai đoạn 2

Theo [llm_agent/README.md](../llm_agent/README.md), các phần dự kiến gồm:

1. Xây dựng MCP Client Wrapper để kết nối AI Agent tới server.
2. Thiết lập system prompt cho trợ lý vận hành nhà máy.
3. Xây dựng các kịch bản Direct Prompt Injection, Indirect Prompt Injection qua SOP, Tool Poisoning và Excessive Agency.
4. Sử dụng hai chế độ lab và nhật ký để so sánh tác động của các kịch bản.

Các giới hạn ở mục 5 cần được tính đến khi thiết kế thí nghiệm, để phân biệt lỗi của lớp ứng dụng với hành vi do AI hoặc prompt injection gây ra.

## 7. Danh mục sản phẩm của giai đoạn 1

| Sản phẩm | Vị trí mã nguồn |
|---|---|
| Cấu hình môi trường PostgreSQL | `docker-compose.yml` |
| Danh sách phụ thuộc Python | `requirements.txt` |
| Cấu hình, kết nối, mô hình và seed/reset dữ liệu | `database/` |
| Server cung cấp 6 MCP tools và 1 resource | `mcp_server/server.py` |
| Kiểm tra quyền, phạm vi, đầu vào | `mcp_server/security.py` |
| Ghi nhật ký theo chế độ lab | `mcp_server/audit.py` |
| Tài liệu SOP được resource sử dụng | `mcp_server/data/fault_handling.txt` |
| Sáu kịch bản kiểm thử nghiệp vụ và chính sách | `tests/test_lab.py` |
| Mô tả kế hoạch tích hợp AI giai đoạn 2 | `llm_agent/README.md` |
