import os

import mysql.connector
from dotenv import load_dotenv


load_dotenv()

# Connect to MySQL
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "Gokul_12345"),
    database=os.getenv("DB_NAME", "arogyam"),
)

cursor = conn.cursor()

try:
    # Delete all pharmacist records
    cursor.execute("DELETE FROM pharmacists")
    print("✓ All pharmacist records deleted")
    
    # Reset auto-increment
    cursor.execute("ALTER TABLE pharmacists AUTO_INCREMENT = 1")
    print("✓ Auto-increment reset to 1")
    
    conn.commit()
    print("\n✓ Database reset successfully!")
    print("You can now register pharmacists with fresh data.")
    
except Exception as e:
    print(f"✗ Error resetting database: {e}")
finally:
    cursor.close()
    conn.close()
