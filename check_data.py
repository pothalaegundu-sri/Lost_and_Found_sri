import sqlite3
import os

# 1. SETUP PATHS
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the main folder, then into 'instance'
db_path = os.path.join(CURRENT_FOLDER, '..', 'instance', 'lost_found_v2.db')

print(f"DEBUG: Checking database at: {os.path.abspath(db_path)}")

if not os.path.exists(db_path):
    print("❌ ERROR: Database file not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n================ DATABASE REPORT ================")

    # ---------------- CHECK USERS ----------------
    try:
        cursor.execute("SELECT * FROM user")
        users = cursor.fetchall()
        print(f"\n👤 TOTAL USERS: {len(users)}")
        if users:
            print(f"{'ID':<5} {'Username':<20}")
            print("-" * 30)
            for user in users:
                # user[0] is ID, user[1] is Username
                print(f"{user[0]:<5} {user[1]:<20}")
    except Exception as e:
        print(f"❌ Error reading Users: {e}")

    # ---------------- CHECK LOST ITEMS ----------------
    try:
        cursor.execute("SELECT * FROM lost_item")
        lost_items = cursor.fetchall()
        print(f"\n🔍 TOTAL LOST ITEMS: {len(lost_items)}")
        
        if lost_items:
            print(f"{'ID':<5} {'Item Name':<20} {'Location':<15} {'Date':<12} {'Image'}")
            print("-" * 75)
            
            for item in lost_items:
                # SAFE GUARD: Convert None to "N/A" to prevent crashes
                i_id = item[0]
                i_name = item[1] if item[1] is not None else "N/A"
                i_loc  = item[3] if item[3] is not None else "N/A"
                i_date = item[4] if item[4] is not None else "N/A"
                i_img  = item[5] if item[5] is not None else "No Image"
                
                # Truncate long names so they fit in the table
                print(f"{i_id:<5} {i_name[:18]:<20} {i_loc[:13]:<15} {i_date[:10]:<12} {i_img}")
                
    except Exception as e:
        print(f"❌ Error reading Lost Items: {e}")

    # ---------------- CHECK FOUND ITEMS ----------------
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='found_item'")
        if cursor.fetchone():
            cursor.execute("SELECT * FROM found_item")
            found_items = cursor.fetchall()
            print(f"\n🎁 TOTAL FOUND ITEMS: {len(found_items)}")
            if found_items:
                for item in found_items:
                    print(item)
        else:
            print("\nℹ️  FOUND ITEMS TABLE: Not created yet (Model missing in app.py)")
    except Exception as e:
        print(f"❌ Error checking Found Items: {e}")

    print("\n=================================================")
    conn.close()