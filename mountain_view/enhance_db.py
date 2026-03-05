import mysql.connector

def migrate_db():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='mountain_view'
        )
        cursor = conn.cursor()

        print("🚀 Starting Database Enhancements...")

        # 1. Add phone to users
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20) AFTER email")
            print("✅ Added 'phone' to users")
        except Exception:
            print("ℹ️ 'phone' column likely exists in users")

        # 1b. Add google_id to users
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(100) NULL AFTER role")
            print("✅ Added 'google_id' to users")
        except Exception:
            print("ℹ️ 'google_id' column likely exists in users")

        # 2. Facilities Table
        print("🔨 Creating 'facilities' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facilities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                icon_class VARCHAR(100) NOT NULL, -- FontAwesome class
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2b. Room Images Table
        print("🔨 Creating 'room_images' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_id INT NOT NULL,
                filename VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
            )
        """)

        # 3. Room Facilities Table
        print("🔨 Creating 'room_facilities' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_facilities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_id INT NOT NULL,
                facility_id INT NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (facility_id) REFERENCES facilities(id) ON DELETE CASCADE
            )
        """)

        # 3b. Add actual_checkout_date, checkout_time to bookings
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN actual_checkout_date DATE NULL AFTER check_out")
            print("✅ Added 'actual_checkout_date' to bookings")
        except Exception:
            print("ℹ️ 'actual_checkout_date' column likely exists in bookings")
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN checkout_time VARCHAR(5) NULL AFTER actual_checkout_date")
            print("✅ Added 'checkout_time' to bookings")
        except Exception:
            print("ℹ️ 'checkout_time' column likely exists in bookings")

        # 4. Seed Default Facilities
        facilities = [
            ("Free Wi-Fi", "fa-solid fa-wifi"),
            ("เครื่องปรับอากาศ", "fa-solid fa-snowflake"),
            ("เครื่องทำน้ำอุ่น", "fa-solid fa-shower"),
            ("ที่จอดรถ", "fa-solid fa-square-parking"),
            ("ทีวี", "fa-solid fa-tv"),
            ("ตู้เย็น", "fa-solid fa-cube") # closest to fridge
        ]
        
        for name, icon in facilities:
            # Check if exists
            cursor.execute("SELECT id FROM facilities WHERE name = %s", (name,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO facilities (name, icon_class) VALUES (%s, %s)", (name, icon))
                print(f"   ➕ Added facility: {name}")

        conn.commit()
        print("✨ Database enhancement completed successfully!")
        
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    migrate_db()
