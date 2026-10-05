import sys
import os
import psycopg2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def init_db():
    """Tạo lại 5 bảng dữ liệu trong PostgreSQL và nạp dữ liệu mẫu phong phú (Minimum 7 tickets)."""
    print(f"Đang kết nối tới PostgreSQL tại {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()
    
    print("Xóa các bảng cũ nếu đã tồn tại...")
    cur.execute("""
        DROP TABLE IF EXISTS configuration_changes CASCADE;
        DROP TABLE IF EXISTS maintenance_tickets CASCADE;
        DROP TABLE IF EXISTS quality_records CASCADE;
        DROP TABLE IF EXISTS machines CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)
    
    print("Đang tạo 5 bảng cơ sở dữ liệu...")
    cur.execute("""
        CREATE TABLE users (
            actor_id VARCHAR(50) PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            role VARCHAR(50) NOT NULL,
            assigned_line VARCHAR(50)
        );

        CREATE TABLE machines (
            machine_id VARCHAR(50) PRIMARY KEY,
            line_id VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            temperature DOUBLE PRECISION NOT NULL,
            speed DOUBLE PRECISION NOT NULL,
            temperature_threshold DOUBLE PRECISION NOT NULL,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE quality_records (
            batch_id VARCHAR(50) PRIMARY KEY,
            machine_id VARCHAR(50) REFERENCES machines(machine_id) ON DELETE CASCADE,
            yield_rate DOUBLE PRECISION NOT NULL,
            defect_rate DOUBLE PRECISION NOT NULL
        );

        CREATE TABLE maintenance_tickets (
            ticket_id SERIAL PRIMARY KEY,
            machine_id VARCHAR(50) REFERENCES machines(machine_id) ON DELETE CASCADE,
            issue TEXT NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_by VARCHAR(50) REFERENCES users(actor_id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE configuration_changes (
            change_id SERIAL PRIMARY KEY,
            machine_id VARCHAR(50) REFERENCES machines(machine_id) ON DELETE CASCADE,
            setting VARCHAR(100) NOT NULL,
            old_value DOUBLE PRECISION NOT NULL,
            new_value DOUBLE PRECISION NOT NULL,
            status VARCHAR(50) NOT NULL,
            requested_by VARCHAR(50) REFERENCES users(actor_id),
            approved_by VARCHAR(50) REFERENCES users(actor_id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    print("Đang nạp dữ liệu mẫu ban đầu phong phú (Seed Data)...")
    # 1. Dữ liệu Người dùng (Users)
    users_data = [
        ('u_op1', 'operator_line_a', 'operator', 'LINE-A'),
        ('u_op2', 'operator_line_b', 'operator', 'LINE-B'),
        ('u_maint1', 'engineer_line_a', 'maintenance_engineer', 'LINE-A'),
        ('u_maint2', 'engineer_line_b', 'maintenance_engineer', 'LINE-B'),
        ('u_sup1', 'supervisor_alpha', 'supervisor', None),
        ('u_sup2', 'supervisor_beta', 'supervisor', None)
    ]
    cur.executemany("INSERT INTO users (actor_id, username, role, assigned_line) VALUES (%s, %s, %s, %s);", users_data)

    # 2. Dữ liệu Máy móc (Machines)
    machines_data = [
        ('M-001', 'LINE-A', 'RUNNING', 75.5, 1500.0, 90.0),
        ('M-002', 'LINE-A', 'FAULT', 95.2, 0.0, 90.0),
        ('M-003', 'LINE-B', 'RUNNING', 68.0, 1200.0, 85.0)
    ]
    cur.executemany("""
        INSERT INTO machines (machine_id, line_id, status, temperature, speed, temperature_threshold, last_updated) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW());
    """, machines_data)

    # 3. Dữ liệu Chất lượng sản phẩm (Quality Records - 5 Lô sản xuất)
    quality_data = [
        ('B-101', 'M-001', 98.5, 1.5),
        ('B-102', 'M-002', 82.0, 18.0),
        ('B-103', 'M-001', 97.8, 2.2),
        ('B-201', 'M-003', 99.2, 0.8),
        ('B-202', 'M-003', 96.5, 3.5)
    ]
    cur.executemany("INSERT INTO quality_records (batch_id, machine_id, yield_rate, defect_rate) VALUES (%s, %s, %s, %s);", quality_data)

    # 4. Dữ liệu Phiếu bảo trì (Maintenance Tickets - 7 Phiếu)
    tickets_data = [
        ('M-001', 'Cảm biến nhiệt độ hiển thị dao động bất thường (75.5C - 88.0C)', 'OPEN', 'u_maint1'),
        ('M-002', 'Động cơ bị quá nhiệt vượt ngưỡng cảnh báo 95.2C', 'IN_PROGRESS', 'u_maint1'),
        ('M-002', 'Lỗi rò rỉ dầu mỡ tại trục quay chính', 'OPEN', 'u_maint1'),
        ('M-003', 'Tiếng ồn rung lắc lạ tại băng tải dây chuyền LINE-B', 'RESOLVED', 'u_maint2'),
        ('M-003', 'Tốc độ quay bị sụt giảm bất ngờ từ 1200 RPM xuống 800 RPM', 'CLOSED', 'u_maint2'),
        ('M-001', 'Bảo trì định kỳ hệ thống làm mát hàng tháng', 'OPEN', 'u_maint1'),
        ('M-002', 'Thay thế cảm biến áp suất khí nén bị hỏng', 'RESOLVED', 'u_maint1')
    ]
    cur.executemany("""
        INSERT INTO maintenance_tickets (machine_id, issue, status, created_by, created_at) 
        VALUES (%s, %s, %s, %s, NOW());
    """, tickets_data)

    # 5. Dữ liệu Yêu cầu Cấu hình (Configuration Changes - 7 Yêu cầu)
    changes_data = [
        ('M-001', 'speed', 1200.0, 1500.0, 'APPROVED', 'u_sup1', 'u_sup1'),
        ('M-003', 'temperature_threshold', 85.0, 90.0, 'PENDING_APPROVAL', 'u_sup1', None),
        ('M-002', 'speed', 1500.0, 0.0, 'APPROVED', 'u_sup1', 'u_sup1'),
        ('M-001', 'temperature_threshold', 90.0, 95.0, 'PENDING_APPROVAL', 'u_sup2', None),
        ('M-003', 'speed', 1200.0, 1800.0, 'PENDING_APPROVAL', 'u_sup1', None),
        ('M-002', 'temperature_threshold', 90.0, 80.0, 'REJECTED', 'u_sup1', 'u_sup2'),
        ('M-001', 'speed', 1500.0, 2200.0, 'PENDING_APPROVAL', 'u_sup2', None)
    ]
    cur.executemany("""
        INSERT INTO configuration_changes (machine_id, setting, old_value, new_value, status, requested_by, approved_by, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());
    """, changes_data)

    conn.commit()
    cur.close()
    conn.close()
    print("Khởi tạo cơ sở dữ liệu với dữ liệu mẫu phong phú (7+ tickets) hoàn tất thành công!")

if __name__ == "__main__":
    init_db()
