from database.config import LAB_MODE, TOOL_PERMISSIONS, SETTING_ALLOWLIST, VALUE_RANGES
from database.models import get_user

class SecurityError(Exception):
    """Ngoại lệ tùy chỉnh được ném ra khi vi phạm chính sách bảo mật hoặc phân quyền."""
    pass

def is_lab_mode_vulnerable() -> bool:
    """Trả về True nếu hệ thống đang chạy ở chế độ thử nghiệm lỗ hổng (vulnerable)."""
    return LAB_MODE == "vulnerable"

def get_actor_or_raise(actor_id: str) -> dict:
    """Kiểm tra sự tồn tại của actor trong DB và trả về thông tin người dùng."""
    if not actor_id or not isinstance(actor_id, str):
        raise SecurityError("Định dạng actor_id không hợp lệ.")
    
    user = get_user(actor_id)
    if not user:
        raise SecurityError(f"Người dùng '{actor_id}' không tồn tại trong hệ thống.")
    return user

def check_role(actor: dict, tool_name: str) -> bool:
    """
    Kiểm tra Phân quyền theo Vai trò (RBAC - Role-Based Access Control).
    Ở chế độ vulnerable, các quy định RBAC tự động được bỏ qua (bypass).
    """
    if is_lab_mode_vulnerable():
        return True
    
    role = actor.get("role")
    allowed_roles = TOOL_PERMISSIONS.get(tool_name, [])
    if role not in allowed_roles:
        raise SecurityError(f"Từ chối Quyền hạn: Vai trò '{role}' không được phép gọi công cụ '{tool_name}'.")
    return True

def check_machine_scope(actor: dict, machine: dict) -> bool:
    """
    Kiểm tra Phân quyền Phạm vi Đối tượng (Scope Authorization) theo Dây chuyền sản xuất.
    Supervisor (assigned_line=None) có quyền xem toàn bộ nhà máy.
    Ở chế độ vulnerable, các quy định Scope tự động được bỏ qua (bypass).
    """
    if is_lab_mode_vulnerable():
        return True

    assigned_line = actor.get("assigned_line")
    machine_line = machine.get("line_id")
    machine_id = machine.get("machine_id")

    # Supervisor có quyền hạn trên toàn cục nhà máy
    if assigned_line is None or actor.get("role") == "supervisor":
        return True

    if assigned_line != machine_line:
        raise SecurityError(
            f"Từ chối Phạm vi: Người dùng '{actor.get('actor_id')}' (được gán cho {assigned_line}) "
            f"không được phép truy cập Máy '{machine_id}' thuộc Dây chuyền '{machine_line}'."
        )
    return True

def check_batch_scope(actor: dict, batch: dict) -> bool:
    """
    Kiểm tra Phân quyền Phạm vi đối với các Lô hàng chất lượng sản phẩm.
    Ở chế độ vulnerable, các quy định Scope tự động được bỏ qua (bypass).
    """
    if is_lab_mode_vulnerable():
        return True

    assigned_line = actor.get("assigned_line")
    batch_line = batch.get("line_id")
    batch_id = batch.get("batch_id")

    if assigned_line is None or actor.get("role") == "supervisor":
        return True

    if assigned_line != batch_line:
        raise SecurityError(
            f"Từ chối Phạm vi: Người dùng '{actor.get('actor_id')}' (được gán cho {assigned_line}) "
            f"không được phép truy cập Lô hàng '{batch_id}' thuộc Dây chuyền '{batch_line}'."
        )
    return True

def validate_setting_and_value(setting: str, value: float) -> bool:
    """
    Kiểm tra tên cấu hình có nằm trong Allowlist và giá trị trong ngưỡng min/max an toàn.
    Ở chế độ vulnerable, kiểm tra đầu vào tự động được bỏ qua (bypass).
    """
    if is_lab_mode_vulnerable():
        return True

    if setting not in SETTING_ALLOWLIST:
        raise SecurityError(f"Cấu hình không hợp lệ: '{setting}' không nằm trong danh sách allowlist {list(SETTING_ALLOWLIST)}.")

    min_val, max_val = VALUE_RANGES[setting]
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        raise SecurityError(f"Giá trị không hợp lệ: '{value}' không phải là một số hợp lệ.")

    if not (min_val <= val_float <= max_val):
        raise SecurityError(f"Vượt ngưỡng An toàn: Giá trị {val_float} của cấu hình '{setting}' phải nằm trong khoảng [{min_val}, {max_val}].")

    return True

def validate_issue(issue: str) -> bool:
    """
    Kiểm tra độ dài và định dạng mô tả sự cố trong phiếu bảo trì.
    Ở chế độ vulnerable, kiểm tra đầu vào tự động được bỏ qua (bypass).
    """
    if is_lab_mode_vulnerable():
        return True

    if not issue or not isinstance(issue, str):
        raise SecurityError("Mô tả sự cố không được để trống.")

    clean_issue = issue.strip()
    if len(clean_issue) < 5 or len(clean_issue) > 500:
        raise SecurityError("Độ dài mô tả sự cố phải từ 5 đến 500 ký tự.")

    return True
