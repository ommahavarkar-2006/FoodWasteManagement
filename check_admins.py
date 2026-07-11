from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Your MySQL root password
app.config['MYSQL_DB'] = 'wastenofood'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_PORT'] = 3306  # Change to 3306 if your XAMPP uses 3306

mysql = MySQL(app)

def check_admins():
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute('SELECT * FROM admins')
            admins = cur.fetchall()
            
            print('Current admin accounts:')
            for admin in admins:
                print(f'ID: {admin["id"]}, Name: {admin["name"]}, Email: {admin["email"]}')
            
            cur.close()
    except Exception as e:
        print(f"Error checking admin accounts: {e}")

if __name__ == "__main__":
    check_admins()