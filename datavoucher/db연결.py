from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import mysql.connector

import os

password = os.getenv('DB_PASSWORD')
print('pw : ',password)

try:
    cnx = mysql.connector.connect(user='root', password='',
                                  host='localhost',
                                  database='testdb')
    print("Connection Successful")
except mysql.connector.Error as err:
    if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)
else:
    cnx.close()



mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password='',
  database="testdb"
)

mycursor = mydb.cursor()

# mycursor.execute("CREATE TABLE user3 (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), email VARCHAR(255), password VARCHAR(255))")



# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:2rw4S@d3f4@localhost/testdb'
# db = SQLAlchemy(app)

# class test(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)

#     def __repr__(self):
#         return '<test %r>' % self.username
    

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:2rw4S@d3f4@localhost/testdb'
db = SQLAlchemy(app)


# 임시 데이터 저장소
users = {}
posts = []

@app.route("/")
def index():
   return "웹 페이지 대문"

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')


    print(username)
    print(password)



    if username in users:
        return make_response('User already exists', 400)
    users[username] = generate_password_hash(password)
    return jsonify({'message': '1'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if username in users and check_password_hash(users[username], password):
        return jsonify({'message': 'Logged in successfully'})
    else:
        return make_response('Invalid username or password', 401)

@app.route('/posts', methods=['POST'])
def create_post():
    data = request.get_json()
    posts.append(data)
    return jsonify({'message': 'Post created successfully'})

@app.route('/posts', methods=['GET'])
def get_posts():
    return jsonify(posts)

@app.route('/users/<username>', methods=['GET'])
def find_user(username):
    if username in users:
        return jsonify({'message': 'User found'})
    else:
        return make_response('User not found', 404)

@app.route('/users/<username>/password', methods=['PUT'])
def change_password(username):
    if username in users:
        data = request.get_json()
        new_password = data.get('new_password')
        users[username] = generate_password_hash(new_password)
        return jsonify({'message': 'Password changed successfully'})
    else:
        return make_response('User not found', 404)

if __name__ == "__main__":
    app.run(debug=True)


