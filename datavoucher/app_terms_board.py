from flask import Flask, Response, request, jsonify, session, render_template, send_from_directory, send_file, redirect, url_for
from flask_session import Session  # 서버 측 세션을 위한 Flask-Session 추가
from flask_mail import Mail, Message
import mysql.connector
import random
from datetime import datetime
import os
import urllib.parse
import copy
import pandas as pd
import datetime
import string
import bcrypt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import string

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  # 세션 데이터를 파일 시스템에 저장
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'jysul8230@gmail.com'
app.config['MAIL_PASSWORD'] = 'orxfvcuiylkunrmb'

mail = Mail(app)
Session(app)  # 앱에 세션 설정 적용

# 랜덤한 문자열 생성 함수 (확인 코드용)
def generate_verification_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# 이메일 전송 및 확인 코드 발급
def send_verification_email(email, verification_code):
    msg = Message('Email Verification', sender='jysul8230@gmail.com', recipients=[email])
    msg.body = f'Your verification code is: {verification_code}'
    mail.send(msg)

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


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # email = request.form['email']
        email = 'hjpark@innopost21.com'

        # 랜덤한 확인 코드 생성
        verification_code = generate_verification_code()

        # 생성된 코드를 세션에 저장
        session['verification_code'] = verification_code
        session['email'] = 'hjpark@innopost21.com'

        # 이메일 전송
        send_verification_email(email, verification_code)
    return jsonify({})

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        entered_code = request.form['code']

        # 세션에서 저장된 코드와 이메일 가져오기
        saved_code = session.get('verification_code')
        email = session.get('email')

        if entered_code == saved_code:
            # 코드 일치 - 본인 인증 완료
            return f'Email verification successful for {email}!'
        else:
            return 'Verification code is incorrect. Please try again.'

    # return render_template('verify.html')

# -----------------------------------약관동의---------------------------------------
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

#---------------------------------가입시 이메일 인증---------------------------------------
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


# ------------------------------------ID 찾기------------------------------------------------------------------------------------------------
def send_sms(phone_number, code):
    # 문자메세지를 받았다 가정하는 함수. 실제로는 sms 수신 API를 구성해야 합니다
    print(f"Sending verification code {code} to phone number {phone_number}")

# 인증번호 생성 및 저장
def generate_and_save_verification_code(phone_number):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(buffered=True)
    # 번호 가입자 테이블에 휴대폰 번호 입력했는지 확인
    cursor.execute("SELECT 1 FROM member_user WHERE PhoneNumber=%s", (phone_number,))
    if not cursor.fetchone():
        print("전화번호가 DB에 없습니다.") # 로깅 또는 다른 처리
        cursor.close()
        conn.close()
        return None # DB에 저장하지 않고 None 반환

    # Generate a random 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    # Save the code to the database with an expiry time of 10 minutes
    expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=10)

    cursor.execute(
        "INSERT INTO phone_verification (PhoneNumber, VerificationCode, Expiry) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE VerificationCode=%s, Expiry=%s",
        (phone_number, code, expiry_time, code, expiry_time)
    )

    conn.commit()
    cursor.close()
    conn.close()

    send_sms(phone_number, code)  # send_sms가 실제 문자를 보낸다고 가정

    return code

# 인증번호 요청
@app.route('/ID_find/request_code', methods=['POST'])
def request_verification_code():
    try:
        phone_number = request.json.get('phone_number')
        session['phone_number'] = phone_number
        if not phone_number:
            return jsonify({"error": "휴대폰 번호 입력은 필수입니다."}), 400

        code = generate_and_save_verification_code(phone_number)
        if code is None:
            return jsonify({"error": "가입하신 전화번호와 일치하지 않습니다."}), 400

        return jsonify({"message": "인증코드를 보냈습니다.!", "verification_code": code}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/ID_find/verify_code', methods=['POST'])
def verify_code_and_get_id():
    try:
        phone_number = session.get('phone_number')
        if phone_number is None:
            return jsonify({"error": "휴대전화 번호가 없습니다. 인증 코드 요청부터 다시 시작해주세요."}), 400
        user_code = request.json.get('code')
        if not phone_number or not user_code:
            return jsonify({"error": "전화번호와 인증 코드는 필수입니다"}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT VerificationCode, Expiry FROM phone_verification WHERE PhoneNumber=%s", (phone_number,))
        actual_code, expiry = cursor.fetchone()

        if datetime.datetime.now() > expiry:
            cursor.close()
            conn.close()
            return jsonify({"error": "인증 코드가 만료되었습니다"}), 400

        if user_code != actual_code:
            cursor.close()
            conn.close()
            return jsonify({"error": "인증 코드가 일치하지 않습니다"}), 400

        cursor.execute("SELECT Email_ID FROM member_user WHERE PhoneNumber=%s", (phone_number,))
        email = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({"email": email, "message": "인증에 성공하였습니다"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#---------------------------------------비밀번호찾기 / 재설정 -----------------------------------------------------

def generate_and_save_password_reset_code(email, phone_number):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT 1 FROM member_user WHERE Email_ID=%s AND PhoneNumber=%s", (email, phone_number))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return None

    code = ''.join(random.choices(string.digits, k=6))
    expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=5)


    cursor.execute(
        "INSERT INTO password_reset (Email_ID, PhoneNumber, ResetCode, Expiry) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE ResetCode=%s, Expiry=%s",
        (email, phone_number, code, expiry_time, code, expiry_time)
    )

    conn.commit()
    cursor.close()
    conn.close()

    send_sms(phone_number, code)
    return code

# 비밀번호 재설정 코드 요청
@app.route('/pw_find/send_code', methods=['POST'])
def send_password_reset_code():
    try:
        email = request.json.get('Email_ID')
        phone_number = request.json.get('phone_number')
        session['phone_number'] = phone_number
        session['email'] = email

        # 이메일과 휴대폰 번호 일치 확인
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT 1 FROM member_user WHERE Email_ID=%s AND PhoneNumber=%s", (email, phone_number))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "입력하신 이메일과 전화번호와 일치하는 계정을 찾을 수 없습니다."}), 400
        cursor.close()
        conn.close()

        code = generate_and_save_verification_code(phone_number)  # 기존 인증 코드 생성 함수 사용
        return jsonify({"message": "인증코드를 보냈습니다.!", "verification_code": code}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/pw_find/reset_password', methods=['POST'])
def reset_password():
    try:
        email = session.get('email') # 이메일도 세션에서 가져오기
        phone_number = session.get('phone_number')
        user_code = request.json.get('code')
        new_password = request.json.get('new_password')
        new_password_confirm = request.json.get('new_password_confirm')

        if not email or not phone_number or not user_code or not new_password or not new_password_confirm:
            return jsonify({"error": "모든 필드를 채워야 합니다"}), 400

        if new_password != new_password_confirm:
            return jsonify({"error": "새 비밀번호가 일치하지 않습니다"}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT VerificationCode, Expiry FROM phone_verification WHERE PhoneNumber=%s", (phone_number,))
        actual_code, expiry = cursor.fetchone()

        if datetime.datetime.now() > expiry:
            cursor.close()
            conn.close()
            return jsonify({"error": "인증 코드가 만료되었습니다"}), 400

        if user_code != actual_code:
            cursor.close()
            conn.close()
            return jsonify({"error": "인증 코드가 일치하지 않습니다"}), 400

        # 이메일과 전화번호를 모두 사용하여 사용자 식별
        cursor.execute("UPDATE member_authenticationinfo SET Password=%s WHERE MemberNo=(SELECT MemberNo FROM member_user WHERE PhoneNumber=%s AND Email_ID=%s)", (new_password, phone_number, email))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "비밀번호가 성공적으로 변경되었습니다"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# -----------------------------------------------회원정보입력----------------------------------------------------

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['Name', 'Password', 'PhoneNumber', 
                       'BusinessRegistrationNumber', 'CompanyAddress', 'EstablishedDate', 'CEO', 'CompanySize', 
                       'CompanyType', 'EmployeeCount', 'InterestKeywords']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    name = data['Name']
    password = data['Password'].encode('utf-8') # 패스워드 인코딩
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())  # 패스워드 해싱
    phone = data['PhoneNumber']
    company_info = {
        'BusinessRegistrationNumber': data['BusinessRegistrationNumber'],
        'CompanyAddress': data['CompanyAddress'],
        'EstablishedDate': data['EstablishedDate'],
        'CEO': data['CEO'],
        'CompanySize': data['CompanySize'],
        'CompanyType': data['CompanyType'],
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

    # try:
        # MariaDB 연결
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # 회원가입 정보 저장
    insert_user_query = 'INSERT INTO member_user (Name, Email_ID, PhoneNumber) VALUES (%s, %s, %s)'
    cursor.execute(insert_user_query, (name, email, phone))
    member_no = cursor.lastrowid  # 새로 생성된 회원 번호 가져오기
    # 패스워드 해싱하여 저장
    insert_auth_query = 'INSERT INTO member_authenticationinfo (MemberNo, Password) VALUES (%s, %s)'
    cursor.execute(insert_auth_query, (member_no, hashed_password.decode('utf-8')))  # 해싱된 패스워드 저장

    # 기업 정보 저장
    insert_company_query = '''
    INSERT INTO member_company (BusinessRegistrationNumber, MemberNo, CompanyAddress, EstablishedDate, 
                                CEO, CompanySize, CompanyType, EmployeeCount, 
                                InterestKeywords)
    VALUES (%s, %s, %s, %s, 
            %s, %s, %s, %s, 
            %s)
    '''
    cursor.execute(insert_company_query, 
                    (company_info['BusinessRegistrationNumber'], member_no, company_info['CompanyAddress'], 
                    company_info['EstablishedDate'], company_info['CEO'], company_info['CompanySize'], 
                    company_info['CompanyType'], company_info['EmployeeCount'], company_info['InterestKeywords']
                    ))

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
    
    # except Exception as e:
    #     print(f"Exception occurred: {e}")
    #     return jsonify({'error': '서버 오류가 발생했습니다'}), 500

# 이메일 중복확인
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

#---------------------------------------로그인--------------------------------------------

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['Email_ID']
    password = data['Password'].encode('utf-8')  # 입력받은 패스워드 인코딩

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # DB에서 해당 이메일의 회원번호와 해시된 패스워드 가져오기
    cursor.execute("SELECT member_authenticationinfo.Password, member_user.MemberNo FROM member_authenticationinfo JOIN member_user ON member_authenticationinfo.MemberNo = member_user.MemberNo WHERE Email_ID=%s", (email,))
    result = cursor.fetchone()
    if result:
        stored_hashed_password = result[0].encode('utf-8')  # DB에 저장된 해시된 패스워드
        user_id = result[1]  # DB에 저장된 회원번호

        # 해시된 패스워드와 입력받은 패스워드 비교
        if bcrypt.checkpw(password, stored_hashed_password):
            # 로그인 성공시 사용자 ID를 세션에 저장
            session['user_id'] = user_id
            return jsonify({'message': '로그인 성공'}), 200

    # 로그인 실패
    return jsonify({'error': '로그인 실패'}), 401


#-------------------------------------------------------------- 로그아웃-------------------------------------------------------------

@app.route('/logout', methods=['POST'])
def logout():
    # 세션에서 사용자 ID 제거
    session.pop('user_id', None)

    return jsonify({'message': '로그아웃 성공'}), 200

#-----------------------------------------------------회원정보 변경------------------------------------------------------------------


@app.route('/update_profile', methods=['POST'])
def update_profile():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({'error': '로그인이 필요합니다'}), 401

    data = request.get_json()

    company_info = {
        'CompanyAddress': data['CompanyAddress'],  
        "CompanySize" : data['CompanySize'],
        'CompanyType': data['CompanyType'],
        'EmployeeCount': data['EmployeeCount'],
        'InterestKeywords': data['InterestKeywords']
    }

    agree_marketing = data['AgreeMarketing']

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    update_company_query = '''
    UPDATE member_company
    SET CompanyAddress=%s, CompanySize=%s,
        CompanyType=%s, EmployeeCount=%s, InterestKeywords=%s
    WHERE MemberNo = %s
    '''
    cursor.execute(update_company_query, 
                    (company_info['CompanyAddress'], company_info['CompanySize'],
                     company_info['CompanyType'], company_info['EmployeeCount'], company_info['InterestKeywords'], user_id
                    ))

    # 마케팅 수신 동의 정보 업데이트
    update_agreement_query = 'UPDATE agreement SET AgreeMarketing=%s WHERE MemberNo=%s'
    cursor.execute(update_agreement_query, (data['AgreeMarketing'], user_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': '프로필 업데이트 완료'}), 200


#-----------------------------------------------------------------------------------------------------------------------------------

@app.route('/post/lists', methods=['GET'])
def get_post_list():
    data = request.get_json()
    MemberNo = data.get('MemberNo')

    sql = '''
            SELECT p.PostID, p.organization, p.notice, p.apply_end, p.tag, p.budget, p.views, CASE WHEN b.bookmarkID IS NOT NULL THEN 'Y' ELSE 'N' END AS bookmarkYN
            FROM POSTS p LEFT JOIN (SELECT * FROM BOOKMARK WHERE MemberNo=%s) b ON p.PostID = b.PostID
          '''

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(sql, (MemberNo,))
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
            'days_left': days_left,
            'tag': post[4],
            'budget': post[5],
            'views': post[6],
            'bookmarkYN': post[7]
        }
        posts_list.append(post_dict)
    total_count = len(posts_list)
    return jsonify({"meta": {"total_count": total_count}, "documents": posts_list})

@app.route('/post/lists/<int:PostID>/download/<string:pfi_originname>', methods=['GET'])
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

@app.route('/post/bookmark/insert', methods=['POST'])
def insert_bookmark():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    data = request.get_json()
    MemberNo = data.get('MemberNo')
    PostID = data.get('PostID')

    sql = "INSERT INTO BOOKMARK (MemberNo, PostID) VALUES (%s, %s)"

    cursor.execute(sql, (MemberNo, PostID))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"result": "success", "description":"즐겨찾기 추가 성공"})

@app.route('/post/bookmark/delete', methods=['DELETE'])
def delete_bookmark():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    data = request.get_json()
    MemberNo = data.get('MemberNo')
    PostID = data.get('PostID')

    sql = "DELETE FROM BOOKMARK WHERE MemberNo=%s AND PostID=%s"

    cursor.execute(sql, (MemberNo, PostID))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"result": "success", "description":"즐겨찾기 삭제 성공"})

@app.route('/post/lists/recommend', methods=['GET'])
def get_post_recommend_list():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    data = request.get_json()
    MemberNo = data.get('MemberNo')

    sql = "SELECT InterestKeywords FROM MEMBER_COMPANY WHERE MemberNo = %s"
    cursor.execute(sql, (MemberNo,))
    interestKeywords = cursor.fetchone()
    interestKeywords = interestKeywords[0]
    sql = '''
            SELECT p.PostID, p.organization, p.notice, p.apply_end, p.budget, p.post_date, p.part, p.department, CASE WHEN b.bookmarkID IS NOT NULL THEN 'Y' ELSE 'N' END AS bookmarkYN
            FROM POSTS p LEFT JOIN (SELECT * FROM BOOKMARK WHERE MemberNo=%s) b ON p.PostID = b.PostID
          '''

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(sql, (MemberNo,))
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
            'days_left': days_left,
            'budget': post[4],
            'post_date': post[5],
            'part': post[6],
            'department': post[7],
            'bookmarkYN': post[8],
        }
        posts_list.append(post_dict)
    columns = ['PostID', 'organization', 'notice', 'days_left', 'budget', 'post_date', 'part', 'department', 'bookmarkYN']
    df = pd.DataFrame(posts_list, columns=columns)
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(df['notice'].tolist())
    target_tfidf = vectorizer.transform([interestKeywords])

    # 코사인 유사도 계산
    similarities = cosine_similarity(tfidf_matrix, target_tfidf)

    # 유사도가 높은 순서대로 인덱스 정렬
    similar_indices = similarities.argsort(axis=0)[::-1].flatten()
    unique_indices = []
    for ind in similar_indices:
        if ind not in unique_indices:
            unique_indices.append(ind)
    recommend_df = df.iloc[unique_indices[:5]]
    
    recommend_data_list = []
    for index, row in recommend_df.iterrows():
        entry = {
            'PostID': row['PostID'],
            'organization': row['organization'],
            'notice': row['notice'],
            'budget': row['budget'],
            'post_date': row['post_date'],
            'part': row['part'],
            'department': row['department'],
            'days_left': row['days_left'],
            'bookmarkYN': row['bookmarkYN']
        }
        recommend_data_list.append(entry)
    total_count = len(recommend_data_list)
    return jsonify({"meta": {"total_count": total_count}, "documents": recommend_data_list})

@app.route('/post/lists/bookmark', methods=['GET'])
def get_post_bookmark_list():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    data = request.get_json()
    MemberNo = data.get('MemberNo')
    sql = "SELECT p.PostID, p.organization, p.notice, p.apply_end, p.tag, p.budget, p.views, CASE WHEN b.bookmarkID IS NOT NULL THEN 'Y' ELSE 'N' END AS bookmarkYN FROM POSTS p LEFT JOIN (SELECT * FROM BOOKMARK WHERE MemberNo=%s) b ON p.PostID = b.PostID WHERE p.PostID in (SELECT PostID FROM BOOKMARK WHERE MemberNo = %s)"
    cursor.execute(sql, (MemberNo, MemberNo))
    bookmark_posts = cursor.fetchall()
    bookmark_posts_list = []
    for post in bookmark_posts:
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
            'days_left': days_left,
            'tag': post[4],
            'budget': post[5],
            'views': post[6],
            'bookmarkYN': post[7],
        }
        bookmark_posts_list.append(post_dict)
    total_count = len(bookmark_posts_list)
    return jsonify({"meta": {"total_count": total_count}, "documents": bookmark_posts_list})

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

@app.route('/post/lists/search', methods=['GET'])
def get_search_post_list():
    data = request.get_json()
    department = data.get('department', [])
    company = data.get('company', [])
    supportType = data.get('supportType', [])
    part = data.get('part', [])
    postDateYN = data.get('postDateYN', 'Y')
    startDate = data.get('startDate')
    endDate = data.get('endDate')
    registerClosingYN = data.get('registerClosingYN', 'Y')
    bookmarkPageYN = data.get('bookmarkPageYN', 'N')
    MemberNo = data.get('MemberNo')
    # startBudget = data.get('startBudget')
    # endBudget = data.get('endBudget')

    conditions = []
    params = []
    params.append(MemberNo)
    # 서울특별시, 경기도, 인천광역시, 강원도, 충청남도, 대전광역시,
    # 충청북도, 세종특별자치시, 부산광역시, 울산광역시, 대구광역시,
    # 경상북도, 경상남도, 전라남도, 광주광역시, 전라북도, 제주특별자치도, 중앙부처
    if department:
        if '중앙부처' in department:
            department.remove('중앙부처')
            department.extend(['산업통상자원부', '고용노동부', '중소벤처기업부', '과학기술정보통신부', '문화체육관광부', '농림축산식품부', '해양수산부', '국토교통부', '환경부', '방위사업청', '보건복지부',
            '여성가족부', '교육부'])
        conditions.append("department IN (" + ','.join('%s' for _ in department) + ")")
        params.extend(department)
    # ['사회적기업', '중소기업', '소상공인', '장애인기업', '여성기업', '벤처기업']
    if company:
        conditions.append("company IN (" + ','.join('%s' for _ in company) + ")")
        params.extend(company)
    # ["일반", "청년", "여성", "장애인"]
    if supportType:
        if '일반' in supportType:
            filtered_list = [item for item in supportType if item != '일반']
            not_like_conditions = ' AND '.join([f"notice NOT LIKE %s" for _ in filtered_list])
            like_conditions = ' OR '.join([f"notice LIKE %s" for _ in filtered_list])        
            conditions.append(f"(({not_like_conditions}) OR ({like_conditions}))")
            params.extend(['%' + keyword + '%' for keyword in filtered_list])
            params.extend(['%' + keyword + '%' for keyword in filtered_list])
        else:
            like_conditions = ' OR '.join([f"notice LIKE %s" for _ in supportType])
            conditions.append(f"({like_conditions})")
            params.extend(['%' + keyword + '%' for keyword in supportType])
    # ['인력']            
    if part:
        conditions.append("part IN (" + ','.join('%s' for _ in part) + ")")
        params.extend(part)
    if postDateYN=='Y':
        if not startDate and endDate:
            conditions.append("post_date <= %s")
            params.extend([endDate])
        elif startDate and not endDate:
            conditions.append("post_date >= %s")
            params.extend([startDate])
        elif startDate and endDate:
            conditions.append("post_date >= %s AND post_date <= %s")
            params.extend([startDate, endDate])
    elif postDateYN=='N':
        if not startDate and endDate:
            conditions.append("apply_end <= %s")
            params.extend([endDate])
        elif startDate and not endDate:
            conditions.append("apply_start >= %s")
            params.extend([startDate])
        elif startDate and endDate:
            conditions.append("apply_start >= %s AND apply_end <= %s")
            params.extend([startDate, endDate])
    if registerClosingYN=='Y':
        today = datetime.now().date()
        conditions.append("apply_end >= %s")
        params.append(str(today))
    
    if bookmarkYN=='Y':
        conditions.append('PostID in (SELECT PostID FROM BOOKMARK WHERE MemberNo = %s)')
        params.append(MemberNo)
    
    if len(conditions) == 0:
        sql = "SELECT p.PostID, p.organization, p.notice, p.apply_end, p.tag, p.budget, p.views, CASE WHEN b.bookmarkID IS NOT NULL THEN 'Y' ELSE 'N' END AS bookmarkYN FROM POSTS p LEFT JOIN (SELECT * FROM BOOKMARK WHERE MemberNo=%s) b ON p.PostID = b.PostID"
    else:
        sql = "SELECT p.PostID, p.organization, p.notice, p.apply_end, p.tag, p.budget, p.views, CASE WHEN b.bookmarkID IS NOT NULL THEN 'Y' ELSE 'N' END AS bookmarkYN FROM POSTS p LEFT JOIN (SELECT * FROM BOOKMARK WHERE MemberNo=%s) b ON p.PostID = b.PostID WHERE "
        
    sql = sql + ' AND '.join(conditions)
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    searched_posts = cursor.fetchall()
    # columns = ['PostID', 'organization', 'notice', 'apply_end', 'tag', 'budget', 'views']
    # df = pd.DataFrame(searched_posts, columns=columns)
    # print(df.head())
    search_posts_list = []
    for post in searched_posts:
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
            'bookmarkYN': post[7]
        }
        search_posts_list.append(post_dict)
    total_count = len(search_posts_list)
    return jsonify({"meta": {"total_count": total_count}, "documents": search_posts_list})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
















