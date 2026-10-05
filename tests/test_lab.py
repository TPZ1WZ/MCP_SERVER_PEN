import pytest
import os
import sys

# Thêm thư mục gốc dự án vào sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.init_db import init_db
from mcp_server.security import is_lab_mode_vulnerable
import mcp_server.server as server

@pytest.fixture(autouse=True)
def setup_fresh_db():
    """Tự động khôi phục DB sạch trước mỗi test case."""
    init_db()

def test_01_get_machine_status_same_line():
    """Truy vấn thiết bị cùng dây chuyền hợp lệ phải thành công ở cả 2 chế độ."""
    res = server.get_machine_status(actor_id="u_op1", machine_id="M-001")
    assert res["success"] is True
    assert res["data"]["machine_id"] == "M-001"
    assert res["data"]["line_id"] == "LINE-A"

def test_02_get_machine_status_cross_line():
    """Nhân viên u_op1 (LINE-A) truy cập máy M-003 (LINE-B)."""
    res = server.get_machine_status(actor_id="u_op1", machine_id="M-003")
    if is_lab_mode_vulnerable():
        assert res["success"] is True  # Phạm vi bị bỏ qua ở chế độ vulnerable
    else:
        assert res["success"] is False  # Từ chối phạm vi (DENY) ở chế độ secure
        assert "Từ chối Phạm vi" in res["error"] or "Scope Denied" in res["error"]

def test_03_create_maintenance_ticket_rbac():
    """Operator u_op1 gọi công cụ create_maintenance_ticket."""
    res = server.create_maintenance_ticket(actor_id="u_op1", machine_id="M-001", issue="Phát hiện tiếng ồn lạ tại bơm")
    if is_lab_mode_vulnerable():
        assert res["success"] is True  # RBAC bị bỏ qua ở chế độ vulnerable
    else:
        assert res["success"] is False  # Từ chối RBAC (DENY) ở chế độ secure
        assert "Từ chối Quyền hạn" in res["error"] or "Access Denied" in res["error"]

def test_04_request_configuration_change_approval_flow():
    """Supervisor u_sup1 đề xuất đổi tốc độ máy M-001."""
    res = server.request_configuration_change(actor_id="u_sup1", machine_id="M-001", setting="speed", new_value=2000.0)
    assert res["success"] is True
    
    if is_lab_mode_vulnerable():
        assert res["change_request"]["status"] == "APPROVED"  # Áp dụng ngay ở chế độ vulnerable
    else:
        assert res["change_request"]["status"] == "PENDING_APPROVAL"  # Chờ duyệt ở chế độ secure

def test_05_approve_configuration_change_rbac():
    """Operator u_op1 cố gắng duyệt yêu cầu thay đổi cấu hình #2 (đang ở trạng thái PENDING_APPROVAL)."""
    res = server.approve_configuration_change(actor_id="u_op1", change_id=2)
    if is_lab_mode_vulnerable():
        assert res["success"] is True  # RBAC bị bỏ qua ở chế độ vulnerable
    else:
        assert res["success"] is False  # Từ chối RBAC (DENY) ở chế độ secure
        assert "Từ chối Quyền hạn" in res["error"] or "Access Denied" in res["error"]

def test_06_input_validation_allowlist_and_range():
    """Đổi tốc độ máy vượt ngưỡng an toàn (99999 RPM)."""
    res = server.request_configuration_change(actor_id="u_sup1", machine_id="M-001", setting="speed", new_value=99999.0)
    if is_lab_mode_vulnerable():
        assert res["success"] is True  # Validation bị bỏ qua ở chế độ vulnerable
    else:
        assert res["success"] is False  # Từ chối Validation (DENY) ở chế độ secure
        assert "Vượt ngưỡng An toàn" in res["error"] or "Validation Out of Range" in res["error"]
