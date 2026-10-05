import os

# Thư mục gốc dự án (/home/luan/project/nha_may_build)
DB_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(DB_DIR)

# Cấu hình kết nối Cơ sở dữ liệu PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "manufacturing_db")
DB_USER = os.getenv("DB_USER", "mcp_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mcp_password")

# Động cơ LAB_MODE ('secure' - an toàn vs 'vulnerable' - lỗ hổng)
LAB_MODE = os.getenv("LAB_MODE", "secure").lower()

# Đường dẫn thư mục và file nhật ký audit log
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_PATH_SECURE = os.path.join(LOG_DIR, "audit_secure.log")
LOG_PATH_VULNERABLE = os.path.join(LOG_DIR, "audit_vulnerable.log")

# Danh sách vai trò và Ma trận Phân quyền Vai trò (RBAC)
ROLES = ["operator", "maintenance_engineer", "supervisor"]

TOOL_PERMISSIONS = {
    "get_machine_status": ["operator", "maintenance_engineer", "supervisor"],
    "get_quality_record": ["maintenance_engineer", "supervisor"],
    "create_maintenance_ticket": ["maintenance_engineer", "supervisor"],
    "get_maintenance_tickets": ["maintenance_engineer", "supervisor"],
    "request_configuration_change": ["supervisor"],
    "approve_configuration_change": ["supervisor"],
}

# Quy tắc kiểm tra đầu vào (Input Validation)
SETTING_ALLOWLIST = {"temperature_threshold", "speed"}

VALUE_RANGES = {
    "temperature_threshold": (50.0, 120.0),  # Đơn vị: Độ C
    "speed": (0.0, 3000.0),                   # Đơn vị: Vòng/phút (RPM)
}

VALID_MACHINE_STATUSES = ["RUNNING", "IDLE", "FAULT", "MAINTENANCE"]
