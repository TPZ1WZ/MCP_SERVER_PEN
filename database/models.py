from psycopg2.extras import RealDictCursor
from database.connection import get_db_connection

def get_user(actor_id: str) -> dict | None:
    """Truy vấn thông tin người dùng theo actor_id."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT actor_id, username, role, assigned_line FROM users WHERE actor_id = %s;", (actor_id,))
            res = cur.fetchone()
            return dict(res) if res else None

def get_machine(machine_id: str) -> dict | None:
    """Truy vấn thông tin và trạng thái thiết bị máy móc theo machine_id."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT machine_id, line_id, status, temperature, speed, temperature_threshold, last_updated 
                FROM machines WHERE machine_id = %s;
            """, (machine_id,))
            res = cur.fetchone()
            if res and res.get('last_updated'):
                res['last_updated'] = res['last_updated'].isoformat()
            return dict(res) if res else None

def get_batch(batch_id: str) -> dict | None:
    """Truy vấn dữ liệu chất lượng lô sản xuất kèm thông tin dây chuyền theo batch_id."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT q.batch_id, q.machine_id, m.line_id, q.yield_rate, q.defect_rate 
                FROM quality_records q
                JOIN machines m ON q.machine_id = m.machine_id
                WHERE q.batch_id = %s;
            """, (batch_id,))
            res = cur.fetchone()
            return dict(res) if res else None

def get_quality_record(batch_id: str) -> dict | None:
    """Wrapper truy vấn bản ghi chất lượng sản phẩm."""
    return get_batch(batch_id)

def create_maintenance_ticket(machine_id: str, issue: str, created_by: str) -> dict:
    """Tạo phiếu yêu cầu bảo trì sửa chữa sự cố mới."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO maintenance_tickets (machine_id, issue, status, created_by, created_at)
                VALUES (%s, %s, 'OPEN', %s, NOW())
                RETURNING ticket_id, machine_id, issue, status, created_by, created_at;
            """, (machine_id, issue, created_by))
            res = cur.fetchone()
            conn.commit()
            if res and res.get('created_at'):
                res['created_at'] = res['created_at'].isoformat()
            return dict(res)

def get_maintenance_tickets(machine_id: str = None) -> list:
    """Lấy danh sách các phiếu bảo trì (tất cả hoặc lọc theo machine_id)."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if machine_id:
                cur.execute("""
                    SELECT ticket_id, machine_id, issue, status, created_by, created_at 
                    FROM maintenance_tickets WHERE machine_id = %s ORDER BY ticket_id DESC;
                """, (machine_id,))
            else:
                cur.execute("""
                    SELECT ticket_id, machine_id, issue, status, created_by, created_at 
                    FROM maintenance_tickets ORDER BY ticket_id DESC;
                """)
            rows = cur.fetchall()
            result = []
            for row in rows:
                r = dict(row)
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].isoformat()
                result.append(r)
            return result

def request_configuration_change(machine_id: str, setting: str, old_value: float, new_value: float, requested_by: str, auto_apply: bool = False) -> dict:
    """Gửi yêu cầu thay đổi thông số cấu hình máy (tốc độ hoặc ngưỡng nhiệt độ)."""
    status = "APPROVED" if auto_apply else "PENDING_APPROVAL"
    approved_by = requested_by if auto_apply else None
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO configuration_changes (machine_id, setting, old_value, new_value, status, requested_by, approved_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING change_id, machine_id, setting, old_value, new_value, status, requested_by, approved_by, created_at;
            """, (machine_id, setting, old_value, new_value, status, requested_by, approved_by))
            change_res = cur.fetchone()
            
            if auto_apply:
                cur.execute(f"UPDATE machines SET {setting} = %s, last_updated = NOW() WHERE machine_id = %s;", (new_value, machine_id))
            
            conn.commit()
            r = dict(change_res)
            if r.get('created_at'):
                r['created_at'] = r['created_at'].isoformat()
            return r

def get_configuration_change(change_id: int) -> dict | None:
    """Truy vấn thông tin yêu cầu thay đổi cấu hình theo change_id."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT change_id, machine_id, setting, old_value, new_value, status, requested_by, approved_by, created_at 
                FROM configuration_changes WHERE change_id = %s;
            """, (change_id,))
            res = cur.fetchone()
            if res and res.get('created_at'):
                res['created_at'] = res['created_at'].isoformat()
            return dict(res) if res else None

def approve_configuration_change(change_id: int, approved_by: str) -> dict:
    """Phê duyệt yêu cầu thay đổi cấu hình đang chờ và cập nhật trực tiếp thông số máy."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT change_id, machine_id, setting, new_value, status 
                FROM configuration_changes WHERE change_id = %s FOR UPDATE;
            """, (change_id,))
            change = cur.fetchone()
            if not change:
                raise ValueError(f"Không tìm thấy yêu cầu thay đổi cấu hình #{change_id}.")
            
            if change['status'] != 'PENDING_APPROVAL':
                raise ValueError(f"Yêu cầu thay đổi cấu hình #{change_id} đã ở trạng thái '{change['status']}'.")
            
            setting = change['setting']
            new_val = change['new_value']
            m_id = change['machine_id']
            
            cur.execute(f"UPDATE machines SET {setting} = %s, last_updated = NOW() WHERE machine_id = %s;", (new_val, m_id))
            cur.execute("""
                UPDATE configuration_changes 
                SET status = 'APPROVED', approved_by = %s 
                WHERE change_id = %s
                RETURNING change_id, machine_id, setting, old_value, new_value, status, requested_by, approved_by, created_at;
            """, (approved_by, change_id))
            res = cur.fetchone()
            conn.commit()
            
            r = dict(res)
            if r.get('created_at'):
                r['created_at'] = r['created_at'].isoformat()
            return r
