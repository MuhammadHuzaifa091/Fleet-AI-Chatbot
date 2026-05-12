import mysql.connector
import os

# Try to get DB credentials from environment or defaults
# Based on common Traccar setup
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="", # default
        database="traccar"
    )
    cursor = conn.cursor()
    
    cursor.execute("DESCRIBE tc_events")
    print("tc_events cols:", [r[0] for r in cursor.fetchall()])
    
    cursor.execute("DESCRIBE tc_devices")
    print("tc_devices cols:", [r[0] for r in cursor.fetchall()])
    
    conn.close()
except Exception as e:
    print("Error:", e)
