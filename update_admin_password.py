from werkzeug.security import generate_password_hash
from flask import Flask
from flask_mysqldb import MySQL

# Create Flask app instance
app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Your MySQL root password
app.config['MYSQL_DB'] = 'wastenofood'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_PORT'] = 3306  # Change to 3306 if your XAMPP uses 3306

mysql = MySQL(app)

def update_admin_password():
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            
            # Hash the new password
            hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
            
            # Update the password for the admin account
            cur.execute("UPDATE admins SET password = %s WHERE email = %s", (hashed_password, 'admin123@gmail.com'))
            
            # Check if any rows were affected
            if cur.rowcount > 0:
                mysql.connection.commit()
                print("Admin password updated successfully!")
            else:
                print("No admin account found with email 'admin123@gmail.com'")
                
                # Try with the other admin email
                cur.execute("UPDATE admins SET password = %s WHERE email = %s", (hashed_password, 'admin@gmail.com'))
                if cur.rowcount > 0:
                    mysql.connection.commit()
                    print("Admin password updated successfully for admin@gmail.com!")
                else:
                    print("No admin accounts found in the database.")
            
            cur.close()
    except Exception as e:
        print(f"Error updating admin password: {e}")

if __name__ == "__main__":
    update_admin_password()