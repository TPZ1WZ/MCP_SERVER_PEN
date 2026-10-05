import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from database.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Khởi tạo Pool kết nối cơ sở dữ liệu PostgreSQL
db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

@contextmanager
def get_db_connection():
    """Quản lý kết nối DB lấy từ Connection Pool và giải phóng sau khi sử dụng."""
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)
