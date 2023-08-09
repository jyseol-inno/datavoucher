from flask import Flask, Response, request, jsonify, session, render_template, send_from_directory, send_file
from flask_session import Session  # 서버 측 세션을 위한 Flask-Session 추가
import mysql.connector
import random
from datetime import datetime
import os
import urllib.parse

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  # 세션 데이터를 파일 시스템에 저장
Session(app)  # 앱에 세션 설정 적용




# MariaDB 연결 정보
db_config = {
    'host': '172.30.1.234',
    'user': 'test',     # 사용자 이름에 맞게 변경해주세요
    'password': 'test', # 비밀번호에 맞게 변경해주세요
    'database': 'testdb3'   # 데이터베이스 이름에 맞게 변경해주세요
}


create_table_queries = [
    '''
    CREATE TABLE IF NOT EXISTS agreement (
    MemberNo INT,
    AgreeService BOOLEAN NOT NULL,
    AgreePrivacy BOOLEAN NOT NULL,
    AgreeMarketing BOOLEAN,
    FOREIGN KEY(MemberNo) REFERENCES member_user(MemberNo)
    );
    ''',

    '''
    CREATE TABLE IF NOT EXISTS phone_verification (
    PhoneNumber VARCHAR(20) PRIMARY KEY,
    VerificationCode VARCHAR(6) NOT NULL,
    Expiry DATETIME NOT NULL
    );
   
    '''
    
]


# MariaDB 연결 및 테이블 생성 쿼리문 여러개 실행
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()
for query in create_table_queries:
    cursor.execute(query)
conn.commit()
cursor.close()
conn.close()

from flask import render_template

@app.route('/')
def index():
    return render_template('index.html')







@app.route('/agreement', methods=['POST'])
def agreement():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['AgreeService', 'AgreePrivacy']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    agree_service = data['AgreeService']
    agree_privacy = data['AgreePrivacy']
    agree_marketing = data.get('AgreeMarketing', False)  # 마케팅 동의는 선택사항이므로 기본값을 False로 설정

    # 세션에 동의 정보 저장 (나중에 회원가입 정보와 함께 데이터베이스에 저장)
    session['agree_service'] = agree_service
    session['agree_privacy'] = agree_privacy
    session['agree_marketing'] = agree_marketing

    return jsonify({'message': '약관 동의가 완료되었습니다'}), 200






@app.route('/email_verification', methods=['POST'])
def email_verification():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['Email_ID']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    email = data['Email_ID']

    # 임의의 인증 코드 생성 (실제로는 이메일로 발송)
    verification_code = '123456'

    # 세션에 이메일과 인증 코드 저장
    session['email'] = email
    session['verification_code'] = verification_code

    return jsonify({'message': '인증 코드가 발송되었습니다'}), 200







@app.route('/verify_code', methods=['POST'])
def verify_code():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['VerificationCode']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    user_code = data['VerificationCode']
    server_code = session.get('verification_code')

    if user_code != server_code:
        return jsonify({'error': '인증 코드가 일치하지 않습니다'}), 400

    # 인증 성공: 세션에 인증 상태 저장
    session['verified'] = True

    return jsonify({'message': '인증에 성공하였습니다'}), 200


# -----------------------ID 찾기------------------------------------------------------------------------------------------
def send_sms(phone_number, code):
    # Fake SMS function. In a real-world scenario, you would integrate with an SMS API to send the code.
    print(f"Sending verification code {code} to phone number {phone_number}")

@app.route('/request_verification_code', methods=['POST'])
def request_verification_code():
    phone_number = request.json.get('phone_number')
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400

    # Check if the phone number exists in the member_user table
    cursor.execute("SELECT 1 FROM member_user WHERE PhoneNumber=%s", (phone_number,))
    if not cursor.fetchone():
        return jsonify({"error": "Phone number not registered"}), 400

    # Generate a random 6-digit code
    code = ''.join(random.choices(string.digits, k=6))

    # Save the code to the database with an expiry time of 10 minutes
    expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=10)
    cursor.execute("INSERT INTO phone_verification (PhoneNumber, VerificationCode, Expiry) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE VerificationCode=%s, Expiry=%s", 
                   (phone_number, code, expiry_time, code, expiry_time))
    conn.commit()

    # Send the code via SMS (fake function for this example)
    send_sms(phone_number, code)

    return jsonify({"message": "Verification code sent!"}), 200

@app.route('/verify_code_and_get_id', methods=['POST'])
def verify_code_and_get_id():
    phone_number = request.json.get('phone_number')
    user_code = request.json.get('code')
    
    if not phone_number or not user_code:
        return jsonify({"error": "Phone number and code are required"}), 400

    cursor.execute("SELECT VerificationCode, Expiry FROM phone_verification WHERE PhoneNumber=%s", (phone_number,))
    result = cursor.fetchone()

    if not result:
        return jsonify({"error": "Verification code not found"}), 400

    actual_code, expiry = result

    if datetime.datetime.now() > expiry:
        return jsonify({"error": "Verification code has expired"}), 400

    if user_code != actual_code:
        return jsonify({"error": "Incorrect verification code"}), 400

    cursor.execute("SELECT Email_ID FROM member_user WHERE PhoneNumber=%s", (phone_number,))
    email = cursor.fetchone()[0]

    return jsonify({"email": email}), 200






@app.route('/send_verification_code', methods=['POST'])
def send_verification_code():
    data = request.get_json()
    phone_number = data.get('PhoneNumber')

    # connect to the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # check if the phone number exists in the member_user table
    cursor.execute('SELECT * FROM member_user WHERE PhoneNumber=%s', (phone_number,))
    if cursor.fetchone() is None:
        return jsonify({'error': '등록되지 않은 전화번호입니다'}), 400

    # generate a random verification code
    verification_code = '123456'

    # calculate the expiry time for the verification code
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)

    # insert the verification code into the phone_verification table
    cursor.execute(
        'INSERT INTO phone_verification (PhoneNumber, VerificationCode, Expiry) VALUES (%s, %s, %s)',
        (phone_number, verification_code, expiry)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': '인증 코드가 발송되었습니다'}), 200


# ----------------------회원정보입력---------------------------#

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['Name', 'Password', 'PhoneNumber', 
                       'BusinessRegistrationNumber', 'EstablishedDate', 'CEO', 'CompanySize', 
                       'CompanyType', 'CompanyAddress', 'EmployeeCount', 'InterestKeywords']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    name = data['Name']
    password = data['Password']
    phone = data['PhoneNumber']
    company_info = {
        'BusinessRegistrationNumber': data['BusinessRegistrationNumber'],
        'CEO': data['CEO'],
        'EstablishedDate': data['EstablishedDate'],
        'CompanySize': data['CompanySize'],
        'CompanyType': data['CompanyType'],
        'CompanyAddress': data['CompanyAddress'],
        'EmployeeCount': data['EmployeeCount'],
        'InterestKeywords': data['InterestKeywords']
    }
       
    # 세션에서 이메일과 약관 동의 정보 가져오기
    email = session.get('email')
    agree_service = session.get('agree_service')
    agree_privacy = session.get('agree_privacy')
    agree_marketing = session.get('agree_marketing')
    verified = session.get('verified')

    if not all([email, agree_service, agree_privacy, verified]):
        return jsonify({'error': '이메일 인증과 약관 동의를 먼저 완료해주세요'}), 400

    
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

        insert_auth_query = 'INSERT INTO member_authenticationinfo (MemberNo, Password) VALUES (%s, %s)'
        cursor.execute(insert_auth_query, (member_no, password))
        
        # 기업 정보 저장
        insert_company_query = """
        INSERT INTO member_company (BusinessRegistrationNumber, CEO, EstablishedDate, 
                            CompanySize, CompanyType, CompanyAddress, EmployeeCount, 
                            InterestKeywords, MemberNo)
        VALUES (%(BusinessRegistrationNumber)s, %(CEO)s, %(EstablishedDate)s, %(CompanySize)s, 
        %(CompanyType)s, %(CompanyAddress)s, %(EmployeeCount)s, %(InterestKeywords)s, %s)
        """
        cursor.execute(insert_company_query, 
                       (company_info['BusinessRegistrationNumber'], company_info['CompanyName'], member_no, 
                        company_info['CompanyAddress'], company_info['CompanyPhoneNumber'], company_info['Industry'], 
                        company_info['EstablishedDate'], company_info['CEO'], company_info['CompanySize']))
        
        # 약관 동의 정보 저장
        insert_agreement_query = 'INSERT INTO agreement (MemberNo, AgreeService, AgreePrivacy, AgreeMarketing) VALUES (%s, %s, %s, %s)'
        cursor.execute(insert_agreement_query, (member_no, agree_service, agree_privacy, agree_marketing))

        conn.commit()

        cursor.close()
        conn.close()

        # 세션에서 이메일과 약관 동의 정보 삭제
        for key in ['email', 'agree_service', 'agree_privacy', 'agree_marketing', 'verification_code']:
            session.pop(key, None)

        return jsonify({'message': '회원가입이 완료되었습니다'}), 201
    except Exception as e:
        return jsonify({'error': '서버 오류가 발생했습니다'}), 500

@app.route('/accounts/check_email', methods=['GET'])
def check_email():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    sql = '''
            SELECT COUNT(*)
            FROM MEMBER_USER
            WHERE Email_ID = %s
          '''
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute(sql, (email,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result[0] > 0:
        return jsonify({"result":"error", "description":"이메일 중복"})
    else:
        return jsonify({"result":"success", "description":"이메일 사용가능"})

@app.route('/post/lists', methods=['GET'])
def get_post_list():
    
    sql = '''
            SELECT PostID, organization, notice, apply_end, tag, budget, views
            FROM POSTS
          '''

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(sql)
    posts = cursor.fetchall()

    posts_list = []
    for post in posts:
        # print(post[3])
        if (post[3]=='-'):
            days_left = '확정안됨'
        else:
            deadline = datetime.strptime(post[3], '%Y-%m-%d').date()
            today = datetime.now().date()
            days_left = (today - deadline).days
        
        post_dict = {
            'PostID': post[0],
            'organization': post[1],
            'notice': post[2], 
            'apply_end': days_left,
            'tag': post[4],
            'budget': post[5],
            'views': post[6],
        }
        posts_list.append(post_dict)
    total_count = len(posts_list)
    return jsonify({"meta": {"total_count": total_count}, "documents": posts_list})

@app.route('/post/lists/<int:PostID>/download/<string:pfi_originname>')
def download_attachment(PostID, pfi_originname):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    sql = '''
            SELECT pfi_originname, pfi_filename
            FROM POST_FILE
            WHERE PostID = %s and pfi_originname = %s
          '''
        
    cursor.execute(sql, (PostID, pfi_originname,))
    attachment = cursor.fetchone()
    pfi_originname = attachment[0]
    pfi_filename = attachment[1]
    attachment_folder = 'attachment_folder'
    script_dir = os.path.dirname(__file__)
    filepath = os.path.join(script_dir, attachment_folder, pfi_filename)
    #print('filepath', filepath)
    return send_file(filepath, as_attachment=True, download_name=pfi_originname)

@app.route('/post/lists/<int:PostID>', methods=['GET'])
def get_post(PostID):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # 조회수 증가
    update_sql = '''
            UPDATE POSTS SET views = views + 1
            WHERE PostID = %s
          '''
    cursor.execute(update_sql, (PostID,))
    conn.commit()

    sql = '''
            SELECT PostID, part, `object`, department, organization, post_date, notice, apply_start, apply_end, budget, overview
            FROM POSTS
            WHERE PostID = %s
          '''

    cursor.execute(sql, (PostID,))
    post = cursor.fetchall()
    post = post[0]
    
    #print('post', post)
    # 첨부파일
    sql = '''
            SELECT pfi_originname, pfi_filename
            FROM POST_FILE
            WHERE PostID = %s
          '''

    cursor.execute(sql, (PostID,))
    attachments = cursor.fetchall()
    attachment_list = []
    for attachment in attachments:
        attachment_list.append(
            {
                'pfi_originname':attachment[0],
                'pfi_filename':attachment[1]
            }
        )
    
    # print('attachment_list', attachment_list)
    
    if (post[8]=='-'):
            days_left = '확정안됨'
    else:
        deadline = datetime.strptime(post[8], '%Y-%m-%d').date()
        today = datetime.now().date()
        days_left = (today - deadline).days
    
    post_dict = {
            'PostID': post[0],
            'part': post[1],
            'object' : post[2],
            'department': post[3],
            'organization': post[4],
            'post_date': post[5],
            'notice': post[6], 
            'days_left': days_left,
            'apply_start': post[7],
            'apply_end': post[8],
            'budget': post[9],
            'overview': post[10],
            'attachments': attachment_list
    }
    return jsonify({"document" : post_dict})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)



















@app.route('/send_password_reset_code', methods=['POST'])
def send_password_reset_code():
    data = request.get_json()
    phone_number = data.get('PhoneNumber')
    email = data.get('Email_ID')

    # connect to the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # check if the phone number and email exist in the member_user table
    cursor.execute('SELECT * FROM member_user WHERE PhoneNumber=%s AND Email_ID=%s', (phone_number, email))
    if cursor.fetchone() is None:
        return jsonify({'error': '등록되지 않은 전화번호 또는 이메일입니다'}), 400

    # generate a random verification code
    verification_code = '123456'

    # calculate the expiry time for the verification code
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)

    # insert the verification code into the phone_verification table
    cursor.execute(
        'INSERT INTO phone_verification (PhoneNumber, VerificationCode, Expiry) VALUES (%s, %s, %s)',
        (phone_number, verification_code, expiry)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': '인증 코드가 발송되었습니다'}), 200
