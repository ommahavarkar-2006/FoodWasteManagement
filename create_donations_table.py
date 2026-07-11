import mysql.connector

try:
    # Connect to MySQL
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='wastenofood'
    )

    cursor = conn.cursor()
    
    # Check if donations_tracking table exists
    cursor.execute("SHOW TABLES LIKE 'donations_tracking'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print('donations_tracking table already exists')
    else:
        print('Creating donations_tracking table...')
        
        # Create the donations_tracking table
        create_table_query = '''
        CREATE TABLE donations_tracking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            donation_id VARCHAR(20) UNIQUE NOT NULL,
            donor_name VARCHAR(100) NOT NULL,
            donor_id INT,
            ngo_id INT,
            food_quantity VARCHAR(50),
            location TEXT,
            status ENUM('Pending', 'Collected', 'Completed') DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            collected_at TIMESTAMP NULL,
            proof_image_path VARCHAR(500),
            ngo_representative VARCHAR(100),
            otp_code VARCHAR(6),
            otp_verified BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (donor_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (ngo_id) REFERENCES ngos(id) ON DELETE SET NULL
        )
        '''
        
        cursor.execute(create_table_query)
        conn.commit()
        print('donations_tracking table created successfully!')
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f'Database error: {err}')
except Exception as e:
    print(f'Error: {e}')