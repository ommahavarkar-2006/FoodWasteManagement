import mysql.connector
from werkzeug.security import generate_password_hash

try:
    # Connect to MySQL
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='wastenofood'
    )

    cursor = conn.cursor()

    # Check if admins table exists and has data
    cursor.execute("SHOW TABLES LIKE 'admins'")
    table_exists = cursor.fetchone()

    if table_exists:
        cursor.execute('SELECT * FROM admins')
        admins = cursor.fetchall()
        print(f'Admin table exists with {len(admins)} records')
        
        for admin in admins:
            print(f'ID: {admin[0]}, Name: {admin[1]}, Email: {admin[2]}')
    else:
        print('Admins table does not exist')

    # Create admin account with email admin123@gmail.com and password admin123
    hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')

    # Insert admin if not exists
    cursor.execute('''
        INSERT INTO admins (name, email, password) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        name = VALUES(name), 
        password = VALUES(password)
    ''', ('Admin', 'admin123@gmail.com', hashed_password))

    conn.commit()
    print('Admin account ensured with email admin123@gmail.com and password admin123')

    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"Database error: {err}")
except Exception as e:
    print(f"Error: {e}")