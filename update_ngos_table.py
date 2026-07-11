import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='wastenofood'
    )

    cursor = conn.cursor()
    
    # First, let's backup the existing data
    print('Backing up existing NGO data...')
    cursor.execute('SELECT * FROM ngos')
    existing_data = cursor.fetchall()
    
    # Get column names
    cursor.execute('DESCRIBE ngos')
    columns = cursor.fetchall()
    column_names = [col[0] for col in columns]
    print(f'Current columns: {column_names}')
    
    # Drop the old table and create new one with proper structure
    print('Updating ngos table structure...')
    
    # Drop the existing table
    cursor.execute('DROP TABLE IF EXISTS ngos')
    
    # Create new table with proper structure
    create_table_query = '''
    CREATE TABLE ngos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        mission TEXT,
        process TEXT,
        activities TEXT,
        impact TEXT,
        contact_email VARCHAR(100),
        contact_phone VARCHAR(15),
        address TEXT,
        website VARCHAR(255),
        logo_url VARCHAR(255),
        image_url VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        is_verified BOOLEAN DEFAULT FALSE,
        registration_number VARCHAR(100) UNIQUE,
        contact_person VARCHAR(100),
        government_id_path VARCHAR(500),
        password VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    '''
    
    cursor.execute(create_table_query)
    print('New ngos table created successfully!')
    
    # If there was existing data, we can try to migrate it
    if existing_data:
        print(f'Migrating {len(existing_data)} existing records...')
        for row in existing_data:
            # Map old columns to new structure
            # This is a basic mapping - you might need to adjust based on your data
            old_id, old_name, old_description, old_contact, old_address = row
            
            # Insert into new table structure
            insert_query = '''
            INSERT INTO ngos (name, description, contact_email, address, is_verified)
            VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(insert_query, (
                old_name or '', 
                old_description or '', 
                old_contact or '', 
                old_address or '',
                True  # Mark as verified since they were in the old system
            ))
        
        conn.commit()
        print('Data migration completed!')
    
    # Verify the new structure
    cursor.execute('DESCRIBE ngos')
    new_columns = cursor.fetchall()
    print('New table structure:')
    for col in new_columns:
        print(f'  {col[0]} - {col[1]}')
    
    cursor.close()
    conn.close()
    
    print('NGO table update completed successfully!')
    
except Exception as e:
    print(f'Error updating NGO table: {e}')