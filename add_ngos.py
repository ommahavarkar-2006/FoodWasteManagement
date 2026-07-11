from werkzeug.security import generate_password_hash
import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='wastenofood'
    )

    cursor = conn.cursor()
    
    # Define the NGOs with their details
    ngos_data = [
        {
            'name': 'Food For All',
            'email': 'foodforall@gmail.com',
            'password': 'foodforall',
            'description': 'We distribute surplus food to poor families and homeless communities.'
        },
        {
            'name': 'Hunger Relief India',
            'email': 'hungerreliefindia@gmail.com',
            'password': 'hungerreliefindia',
            'description': 'A nationwide movement ensuring leftover food reaches the needy.'
        },
        {
            'name': 'Robin Food Mission',
            'email': 'robinfoodmission@gmail.com',
            'password': 'robinfoodmission',
            'description': 'We rescue food from events, restaurants, and markets.'
        },
        {
            'name': 'Feeding Smiles Foundation',
            'email': 'feedingsmilesfoundation@gmail.com',
            'password': 'feedingsmilesfoundation',
            'description': 'A youth-led initiative providing meals to underprivileged kids.'
        },
        {
            'name': 'Green Earth Food Rescue',
            'email': 'greenearthfoodrescue@gmail.com',
            'password': 'greenearthfoodrescue',
            'description': 'We work with supermarkets to save unsold but edible food.'
        },
        {
            'name': 'Humanity First Kitchen',
            'email': 'humanityfirstkitchen@gmail.com',
            'password': 'humanityfirstkitchen',
            'description': 'Runs free kitchens for anyone who needs a meal.'
        }
    ]
    
    for ngo in ngos_data:
        # Hash the password
        hashed_password = generate_password_hash(ngo['password'], method='pbkdf2:sha256')
        
        # Check if NGO already exists
        cursor.execute('SELECT id FROM ngos WHERE contact_email = %s', (ngo['email'],))
        existing_ngo = cursor.fetchone()
        
        if existing_ngo:
            print(f'NGO {ngo["name"]} already exists.')
            continue
        
        # Insert the NGO into the database
        cursor.execute('''
            INSERT INTO ngos (name, description, contact_email, is_active, is_verified, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            ngo['name'],
            ngo['description'],
            ngo['email'],
            True,  # is_active
            True,  # is_verified
            hashed_password
        ))
        
        print(f'Added NGO: {ngo["name"]}')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('NGOs added successfully!')

except Exception as e:
    print(f'Error: {e}')