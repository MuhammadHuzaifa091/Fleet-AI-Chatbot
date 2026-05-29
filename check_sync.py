import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def check():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_SERVER", "localhost"),
            user=os.getenv("DB_USER", "traccar"),
            password=os.getenv("DB_PASSWORD", "traccar12344321"),
            database=os.getenv("DB_NAME", "traccar"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tc_devices")
            print(f"DEVICES: {cursor.fetchone()[0]}")
            cursor.execute("SELECT COUNT(*) FROM tc_users")
            print(f"USERS: {cursor.fetchone()[0]}")
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check()
