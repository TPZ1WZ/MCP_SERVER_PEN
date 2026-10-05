import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.init_db import init_db

if __name__ == "__main__":
    print("Đang khôi phục cơ sở dữ liệu PostgreSQL về trạng thái ban đầu...")
    init_db()
    print("Khôi phục hoàn tất.")
