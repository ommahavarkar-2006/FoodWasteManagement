import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        database='wastenofood',
        user='root',
        password=''
    )
    cursor = conn.cursor()
    
    # Create leftover_food_reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leftover_food_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_type ENUM('Wedding', 'Party', 'Hotel', 'Function') NOT NULL,
            event_date DATE NOT NULL,
            event_time TIME NOT NULL,
            location TEXT NOT NULL,
            latitude DECIMAL(10, 8),
            longitude DECIMAL(11, 8),
            people_invited INT NOT NULL,
            people_ate INT NOT NULL,
            food_left_kg DECIMAL(10, 2),
            food_left_plates INT,
            food_type ENUM('Veg', 'Non-Veg', 'Both') NOT NULL,
            food_photo_path VARCHAR(255),
            kitchen_photo_path VARCHAR(255),
            organizer_name VARCHAR(100) NOT NULL,
            contact_number VARCHAR(15) NOT NULL,
            status ENUM('Reported', 'NGO_Assigned', 'Picked_Up', 'Completed', 'Cancelled') DEFAULT 'Reported',
            ngo_id INT,
            ngo_name VARCHAR(200),
            proof_image_path VARCHAR(255),
            donor_confirmed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (ngo_id) REFERENCES ngos(id) ON DELETE SET NULL
        )
    """)
    
    print("✅ Leftover food reports table created successfully!")
    
    # Verify table structure
    cursor.execute("DESCRIBE leftover_food_reports")
    columns = cursor.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")