import os
import sys
import logging
from mcp.server.fastmcp import FastMCP

from database.config import LAB_MODE
from mcp_server.audit import audit_log
from mcp_server.security import (
    SecurityError,
    get_actor_or_raise,
    check_role,
    check_machine_scope,
    check_batch_scope,
    validate_setting_and_value,
    validate_issue,
    is_lab_mode_vulnerable
)
import database.models as db

# LƯU Ý QUAN TRỌNG VỀ GIAO THỨC STDIO TRANSPORT:
# Tất cả log debug BẮT BUỘC phải đẩy sang sys.stderr để bảo vệ luồng stdin/stdout dùng riêng cho giao thức JSON-RPC của MCP.
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ManufacturingMCPServer")

logger.info(f"Khởi động Manufacturing MCP Server ở chế độ LAB_MODE='{LAB_MODE}'...")

# Khởi tạo Server MCP bằng FastMCP
mcp = FastMCP("Manufacturing Operations Server")

# --------------------------------------------------------------------
# MCP RESOURCE (Tài nguyên chỉ đọc)
# --------------------------------------------------------------------
@mcp.resource("manual://fault-handling")
def get_fault_handling_manual() -> str:
    """
    Cung cấp Tài liệu Cẩm nang Quy trình Tiêu chuẩn (SOP) Xử lý Sự cố & An toàn Thiết bị.
    Chứa thông tin ngưỡng nhiệt độ, quy trình hiệu chuẩn tốc độ và luồng phê duyệt 2 người.
    """
    server_dir = os.path.dirname(os.path.abspath(__file__))
    manual_path = os.path.join(server_dir, "data", "fault_handling.txt")
    if not os.path.exists(manual_path):
        return "Không tìm thấy file Cẩm nang SOP Xử lý Sự cố."
    with open(manual_path, "r", encoding="utf-8") as f:
        return f.read()

# --------------------------------------------------------------------
# MCP TOOLS (Công cụ thực thi)
# --------------------------------------------------------------------

@mcp.tool()
def get_machine_status(actor_id: str, machine_id: str) -> dict:
    """
    Tra cứu trạng thái vận hành, nhiệt độ, tốc độ, dây chuyền và ngưỡng an toàn hiện tại của máy.
    
    Tham số:
        actor_id: Mã định danh của người dùng gọi công cụ (ví dụ: 'u_op1', 'u_sup1').
        machine_id: Mã máy cần truy vấn (ví dụ: 'M-001', 'M-002').
    """
    tool_name = "get_machine_status"
    target_resource = f"machine:{machine_id}"
    actor = None
    try:
        actor = get_actor_or_raise(actor_id)
        role = actor["role"]
        
        check_role(actor, tool_name)
        
        machine = db.get_machine(machine_id)
        if not machine:
            raise SecurityError(f"Máy '{machine_id}' không tồn tại.")
            
        check_machine_scope(actor, machine)
        
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id}, target_resource, "ALLOW", machine, True)
        return {"success": True, "data": machine}
        
    except SecurityError as se:
        role = actor["role"] if actor else "UNKNOWN"
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id}, target_resource, "DENY", str(se), False)
        return {"success": False, "error": str(se)}
    except Exception as e:
        logger.error(f"Lỗi trong {tool_name}: {e}")
        return {"success": False, "error": f"Lỗi Nội bộ Server: {str(e)}"}


@mcp.tool()
def get_quality_record(actor_id: str, batch_id: str) -> dict:
    """
    Tra cứu thông số chất lượng sản phẩm (tỷ lệ sản phẩm đạt yield_rate, tỷ lệ lỗi defect_rate) của lô hàng.
    
    Tham số:
        actor_id: Mã định danh của người dùng gọi công cụ.
        batch_id: Mã lô sản xuất cần truy vấn (ví dụ: 'B-101', 'B-201').
    """
    tool_name = "get_quality_record"
    target_resource = f"batch:{batch_id}"
    actor = None
    try:
        actor = get_actor_or_raise(actor_id)
        role = actor["role"]
        
        check_role(actor, tool_name)
        
        batch = db.get_quality_record(batch_id)
        if not batch:
            raise SecurityError(f"Lô hàng '{batch_id}' không tồn tại.")
            
        check_batch_scope(actor, batch)
        
        audit_log(actor_id, role, tool_name, {"batch_id": batch_id}, target_resource, "ALLOW", batch, True)
        return {"success": True, "data": batch}
        
    except SecurityError as se:
        role = actor["role"] if actor else "UNKNOWN"
        audit_log(actor_id, role, tool_name, {"batch_id": batch_id}, target_resource, "DENY", str(se), False)
        return {"success": False, "error": str(se)}
    except Exception as e:
        logger.error(f"Lỗi trong {tool_name}: {e}")
        return {"success": False, "error": f"Lỗi Nội bộ Server: {str(e)}"}


@mcp.tool()
def create_maintenance_ticket(actor_id: str, machine_id: str, issue: str) -> dict:
    """
    Tạo phiếu yêu cầu bảo trì mới cho thiết bị gặp sự cố hoặc cảnh báo quá nhiệt.
    
    Tham số:
        actor_id: Mã người dùng tạo phiếu (Kỹ sư bảo trì hoặc Supervisor).
        machine_id: Mã máy cần bảo trì.
        issue: Mô tả chi tiết sự cố hỏng hóc quan sát được (từ 5 đến 500 ký tự).
    """
    tool_name = "create_maintenance_ticket"
    target_resource = f"machine:{machine_id}"
    actor = None
    try:
        actor = get_actor_or_raise(actor_id)
        role = actor["role"]
        
        check_role(actor, tool_name)
        
        machine = db.get_machine(machine_id)
        if not machine:
            raise SecurityError(f"Máy '{machine_id}' không tồn tại.")
            
        check_machine_scope(actor, machine)
        validate_issue(issue)
        
        ticket = db.create_maintenance_ticket(machine_id, issue, actor_id)
        
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id, "issue": issue}, target_resource, "ALLOW", ticket, True)
        return {"success": True, "ticket": ticket}
        
    except SecurityError as se:
        role = actor["role"] if actor else "UNKNOWN"
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id, "issue": issue}, target_resource, "DENY", str(se), False)
        return {"success": False, "error": str(se)}
    except Exception as e:
        logger.error(f"Lỗi trong {tool_name}: {e}")
        return {"success": False, "error": f"Lỗi Nội bộ Server: {str(e)}"}


@mcp.tool()
def get_maintenance_tickets(actor_id: str, machine_id: str = None) -> dict:
    """
    Tra cứu danh sách các phiếu bảo trì sự cố (tất cả các phiếu hoặc lọc theo máy cụ thể).
    
    Tham số:
        actor_id: Mã người dùng gọi công cụ.
        machine_id: Mã máy cần lọc phiếu (tùy chọn).
    """
    tool_name = "get_maintenance_tickets"
    target_resource = f"machine:{machine_id}" if machine_id else "machine:ALL"
    actor = None
    try:
        actor = get_actor_or_raise(actor_id)
        role = actor["role"]
        
        check_role(actor, tool_name)
        
        if machine_id:
            machine = db.get_machine(machine_id)
            if not machine:
                raise SecurityError(f"Máy '{machine_id}' không tồn tại.")
            check_machine_scope(actor, machine)
            
        tickets = db.get_maintenance_tickets(machine_id)
        
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id}, target_resource, "ALLOW", {"count": len(tickets)}, True)
        return {"success": True, "tickets": tickets}
        
    except SecurityError as se:
        role = actor["role"] if actor else "UNKNOWN"
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id}, target_resource, "DENY", str(se), False)
        return {"success": False, "error": str(se)}
    except Exception as e:
        logger.error(f"Lỗi trong {tool_name}: {e}")
        return {"success": False, "error": f"Lỗi Nội bộ Server: {str(e)}"}


@mcp.tool()
def request_configuration_change(actor_id: str, machine_id: str, setting: str, new_value: float) -> dict:
    """
    Đề xuất thay đổi thông số cấu hình máy (tốc độ 'speed' hoặc ngưỡng quá nhiệt 'temperature_threshold').
    Ở chế độ secure: Tạo yêu cầu ở trạng thái 'PENDING_APPROVAL' chờ Supervisor duyệt.
    Ở chế độ vulnerable: Tự động áp dụng giá trị mới trực tiếp vào máy.
    
    Tham số:
        actor_id: Mã người dùng gửi đề xuất.
        machine_id: Mã máy cần đổi thông số.
        setting: Tên cấu hình ('speed' hoặc 'temperature_threshold').
        new_value: Giá trị số đề xuất mới.
    """
    tool_name = "request_configuration_change"
    target_resource = f"machine:{machine_id}:{setting}"
    actor = None
    try:
        actor = get_actor_or_raise(actor_id)
        role = actor["role"]
        
        check_role(actor, tool_name)
        
        machine = db.get_machine(machine_id)
        if not machine:
            raise SecurityError(f"Máy '{machine_id}' không tồn tại.")
            
        check_machine_scope(actor, machine)
        validate_setting_and_value(setting, new_value)
        
        old_value = float(machine.get(setting, 0.0))
        
        # Hành vi Dual-Mode: Chế độ vulnerable tự động áp dụng thông số ngay mà không cần chờ duyệt
        auto_apply = is_lab_mode_vulnerable()
        
        change_rec = db.request_configuration_change(
            machine_id=machine_id,
            setting=setting,
            old_value=old_value,
            new_value=float(new_value),
            requested_by=actor_id,
            auto_apply=auto_apply
        )
        
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id, "setting": setting, "new_value": new_value}, target_resource, "ALLOW", change_rec, True)
        return {"success": True, "change_request": change_rec}
        
    except SecurityError as se:
        role = actor["role"] if actor else "UNKNOWN"
        audit_log(actor_id, role, tool_name, {"machine_id": machine_id, "setting": setting, "new_value": new_value}, target_resource, "DENY", str(se), False)
        return {"success": False, "error": str(se)}
    except Exception as e:
        logger.error(f"Lỗi trong {tool_name}: {e}")
        return {"success": False, "error": f"Lỗi Nội bộ Server: {str(e)}"}


@mcp.tool()
def approve_configuration_change(actor_id: str, change_id: int) -> dict:
    """
    Phê duyệt yêu cầu thay đổi cấu hình đang chờ và cập nhật trực tiếp thông số mới cho máy.
    
    Tham số:
        actor_id: Mã Supervisor thực hiện phê duyệt.
        change_id: Mã yêu cầu thay đổi cấu hình.
    """
    tool_name = "approve_configuration_change"
    target_resource = f"change:{change_id}"
    actor = None
    try:
        actor = get_actor_or_raise(actor_id)
        role = actor["role"]
        
        check_role(actor, tool_name)
        
        change_rec = db.get_configuration_change(change_id)
        if not change_rec:
            raise SecurityError(f"Không tìm thấy yêu cầu thay đổi cấu hình #{change_id}.")
            
        machine = db.get_machine(change_rec["machine_id"])
        if machine:
            check_machine_scope(actor, machine)
            
        result_rec = db.approve_configuration_change(change_id, actor_id)
        
        audit_log(actor_id, role, tool_name, {"change_id": change_id}, target_resource, "ALLOW", result_rec, True)
        return {"success": True, "approved_change": result_rec}
        
    except SecurityError as se:
        role = actor["role"] if actor else "UNKNOWN"
        audit_log(actor_id, role, tool_name, {"change_id": change_id}, target_resource, "DENY", str(se), False)
        return {"success": False, "error": str(se)}
    except Exception as e:
        logger.error(f"Lỗi trong {tool_name}: {e}")
        return {"success": False, "error": f"Lỗi Nội bộ Server: {str(e)}"}


if __name__ == "__main__":
    logger.info("Khởi động MCP Server chạy giao thức stdio transport...")
    mcp.run(transport="stdio")
