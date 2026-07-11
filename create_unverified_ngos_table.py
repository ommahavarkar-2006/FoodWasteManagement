import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='wastenofood'
    )

    cursor = conn.cursor()
    
    # Check if unverified_ngos table exists
    cursor.execute("SHOW TABLES LIKE 'unverified_ngos'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print('unverified_ngos table already exists')
    else:
        print('Creating unverified_ngos table...')
        
        create_table_query = '''
        CREATE TABLE unverified_ngos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            address TEXT NOT NULL,
            registration_number VARCHAR(100) UNIQUE NOT NULL,
            government_id_path VARCHAR(500) NOT NULL,
            contact_person VARCHAR(100) NOT NULL,
            phone VARCHAR(15) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            is_approved BOOLEAN DEFAULT FALSE,
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        '''
        
        cursor.execute(create_table_query)
        conn.commit()
        print('unverified_ngos table created successfully!')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')