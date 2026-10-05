import os
import json
from datetime import datetime, timezone
from database.config import LOG_DIR, LOG_PATH_SECURE, LOG_PATH_VULNERABLE, LAB_MODE

# Tự động tạo thư mục logs nếu chưa tồn tại
os.makedirs(LOG_DIR, exist_ok=True)

def audit_log(
    actor_id: str,
    role: str,
    tool_name: str,
    arguments: dict,
    target_resource: str,
    authorization_decision: str,  # 'ALLOW' (cho phép) hoặc 'DENY' (từ chối)
    result: any,
    success: bool
):
    """
    Hệ thống ghi nhật ký kiểm toán (Audit Logger) dạng JSON-lines append-only.
    Ghi nhận lại mọi lượt gọi Tool bất kể quyết định phân quyền thành công hay thất bại.
    """
    log_file = LOG_PATH_VULNERABLE if LAB_MODE == "vulnerable" else LOG_PATH_SECURE

    # Định dạng thời gian ISO 8601 UTC
    timestamp = datetime.now(timezone.utc).isoformat()

    entry = {
        "timestamp": timestamp,
        "actor_id": actor_id,
        "role": role,
        "tool_name": tool_name,
        "arguments": arguments,
        "target_resource": target_resource,
        "authorization_decision": authorization_decision,
        "result": result,
        "success": success,
        "lab_mode": LAB_MODE
    }

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        import sys
        sys.stderr.write(f"[LỖI GHI AUDIT LOG] Không thể ghi file log: {e}\n")
