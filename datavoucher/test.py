from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# MariaDB 연결 정보
db_config = {
    'host': 'localhost',
    'user': 'root',     # 사용자 이름에 맞게 변경해주세요
    'password': 'root', # 비밀번호에 맞게 변경해주세요
    'database': 'testdb3'   # 데이터베이스 이름에 맞게 변경해주세요
}

# 각각의 테이블 생성 쿼리
create_table_queries = [
    """
    CREATE TABLE IF NOT EXISTS member_user (
        MemberNo INT AUTO_INCREMENT PRIMARY KEY,
        Email_ID VARCHAR(255) NOT NULL,
        Name VARCHAR(255) NOT NULL,
        PhoneNumber VARCHAR(20),
        Status ENUM('ACTIVE', 'WITHDRAWN') DEFAULT 'ACTIVE'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS member_authenticationinfo (
        MemberNo INT,
        Password VARCHAR(255) NOT NULL,
        PhoneNumber VARCHAR(20),
        FOREIGN KEY (MemberNo) REFERENCES member_user(MemberNo)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS member_company (
        CompanyID INT AUTO_INCREMENT PRIMARY KEY,
        BusinessRegistrationNumber VARCHAR(255) UNIQUE,
        CompanyName VARCHAR(255),
        MemberNo INT,
        CompanyAddress ENUM('서울', '경기', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경북', '경남', '전북', '전남', '충북', '충남', '강원', '제주', '해외'),
        CompanyPhoneNumber VARCHAR(20),
        Industry VARCHAR(255),
        EstablishedDate DATE,
        CEO VARCHAR(255),
        CompanySize ENUM('소상공인', '중소기업', '중견기업', '대기업'),
        FOREIGN KEY(MemberNo) REFERENCES member_user(MemberNo)
    );

    """
]

# MariaDB 연결 및 테이블 생성
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()
for query in create_table_queries:
    cursor.execute(query)
conn.commit()
cursor.close()
conn.close()


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    print("request.get_json() : " ,data)
    # 필수 필드 확인
    if 'Name' not in data or 'Email_ID' not in data or 'Password' not in data or 'PhoneNumber' not in data:
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    name = data['Name']
    email = data['Email_ID']
    password = data['Password']
    phone = data['PhoneNumber']

    try:
        # MariaDB 연결
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 이메일 중복 확인
        cursor.execute('SELECT * FROM member_user WHERE Email_ID=%s', (email,))
        if cursor.fetchone() is not None:
            return jsonify({'error': '이미 가입된 이메일입니다'}), 409

        # 회원가입 정보 저장
        insert_user_query = 'INSERT INTO member_user (Name, Email_ID, PhoneNumber) VALUES (%s, %s, %s)'
        cursor.execute(insert_user_query, (name, email, phone))
        member_no = cursor.lastrowid  # 새로 생성된 회원 번호 가져오기
        print("member no : ", member_no)
        insert_auth_query = 'INSERT INTO member_authenticationinfo (MemberNo, Password) VALUES (%s, %s)'
        cursor.execute(insert_auth_query, (member_no, password))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'message': '회원가입이 완료되었습니다'}), 201
    except Exception as e:
        return jsonify({'error': '서버 오류가 발생했습니다'}), 500


if __name__ == '__main__':
    app.run(debug=True)
























'''
FLASK 웹 애플리케이션을 개발모드에서 실행하는 명령어
일단 플라스크 애플리케이션이 있는 디렉토리로 이동  
리눅스환경에서
FLASK_APP=app.py FLASK_DEBUG=1 flask run

윈도우환경에서  
set FLASK_APP=app.py
set FLASK_DEBUG=1
flask run
  

개인정보 숨기기 버전
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

@app.route("/hello", methods=['GET'])
def hello():
  return "hello world"

@app.route("/signup",methods=['POST'])
def sign_up():
    if not request.json or not 'name' in request.json or not 'email' in request.json or not 'password' in request.json or not 'profile' in request.json:
        abort(400)
    user = request.json
    response = {
        'name': user['name'],
        'email': user['email'],
        'profile': user['profile']
    }
    return jsonify(response), 200

if __name__ == "__main__":
  app.run(port=8000)

  '''