from flask import Flask, Response, request, jsonify, session, render_template, send_from_directory, send_file, redirect, url_for
from flask_session import Session  
from flask_mail import Mail, Message
from flask_restx import Api, Resource, fields, reqparse
import mysql.connector
import random
from datetime import datetime
import os
import urllib.parse
import copy
import pandas as pd
import string
import bcrypt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from functools import wraps
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail




app = Flask(__name__)
api = Api(app, version='1.0', title='API 문서', description='Swagger 문서', doc="/api-docs")
test_api = api.namespace('test', description='조회 API')


app.config['SESSION_TYPE'] = 'filesystem'  # 세션 유형 설정, 데이터를 파일 시스템에 저장
app.config['SESSION_FILE_DIR'] = 'flask_session' # 세션 파일이 저장될 디렉터리 설정 (옵션)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'jysul8230@gmail.com'

MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD

mail = Mail(app)
# Flask-Session 확장 초기화
sess = Session()
sess.init_app(app)


# MariaDB 연결 정보
db_config = {
    'host': '172.30.1.234',
    'user': 'test',     # 사용자 이름에 맞게 변경해주세요
    'password': 'test', # 비밀번호에 맞게 변경해주세요
    'database': 'testdb3'   # 데이터베이스 이름에 맞게 변경해주세요
}

# 랜덤한 문자열 생성 함수 (확인 코드용)
def generate_verification_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# 이메일 전송 및 확인 코드 발급
def send_verification_email(email, verification_code):
    msg = Message('Email Verification', sender='jysul8230@gmail.com', recipients=[email])
    msg.body = f'Your verification code is: {verification_code}'
    mail.send(msg)


# def send_verification_email2(email, verification_code):
#     message = Mail(
#         from_email='hjpark@innopost21.com', # 발신자 이메일 주소
#         to_emails=email, # 수신자 이메일 주소
#         subject='Email Verification', # 제목
#         plain_text_content=f'Your verification code is: {verification_code}') # 내용

#     # SendGrid API 클라이언트 초기화
#     sg = SendGridAPIClient('YSG.AoPSos2JR2qaCUoSDVx4yA.slbtPScOzb96Ax7Rv2Zrm---H-vPV9R8QtG3mIn1egs')

#     # 이메일 전송
#     response = sg.send(message)

#     return response.status_code


model = api.model('ModelName', {
    'field1': fields.String(required=True, description='Description of field 1'),
    'field2': fields.Integer(required=True, description='Description of field 2')
})

#----------------------------------------회원가입------------------------------------------------------
@test_api.route('/signup/info')
class signup_info(Resource):
    @api.expect(model, validate=True)
    def post(self):
        # JSON 데이터 한 번에 받기
        data = api.payload

        # 약관동의
        required_agreements = ['AgreeService', 'AgreePrivacy']
        for agreement in required_agreements:
            if data.get(agreement) is not True:
                return jsonify({'error': '필수 약관에 동의해주세요'}), 400
        
        # 약관 동의 정보 세션에 저장
        session['agree_service'] = data['AgreeService']
        session['agree_privacy'] = data['AgreePrivacy']
        session['agree_marketing'] = data.get('AgreeMarketing', False) # 마케팅 동의는 선택사항이므로 기본값을 False로 설정

        # 회원정보 필수 필드 확인
        required_fields = ['Email_ID', 'Name', 'Password', 'PhoneNumber', 
                        'BusinessRegistrationNumber', 'CompanyAddress', 'EstablishedDate', 'CEO', 'CompanySize', 
                        'CompanyType', 'EmployeeCount', 'InterestKeywords']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': '모든 회원정보를 입력해주세요'}), 400

        email = data['Email_ID']
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

        
        
        # 세션에 정보 저장
        session['signup_info'] = {
        'Email_ID': email,
        'Name': name,
        'hashed_password': hashed_password.decode('utf-8'),
        'PhoneNumber': phone,
        'company_info': company_info
        }



        # MariaDB 연결
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 이메일 중복확인 
        cursor.execute("SELECT COUNT(*) FROM member_user WHERE Email_ID=%s", (email,))
        result = cursor.fetchone()
        
        if result[0] > 0:
            return jsonify({"result":"error", "description":"이미 가입된 이메일입니다."}), 400
        
        # 이메일 인증 코드 발송
        
        verification_code = generate_verification_code()
        session['verification_code'] = verification_code
        session['email'] = email    
        send_verification_email(email, verification_code)
            

        return jsonify({'message': '회원 정보가 저장되었습니다. 이메일 인증을 진행해주세요.'}), 200


@app.route('/signup/verify', methods=['POST'])
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

    return jsonify({'result': '인증에 성공하였습니다'}), 200      

@app.route('/signup/complete', methods=['POST'])
def signup_complete():
    verified = session.get('verified')
    if verified is not True:
        return jsonify({'error': '이메일 인증을 먼저 완료해주세요'}), 400

    # 세션에서 정보 가져오기
    signup_info = session.get('signup_info')
    print("세션에서 가져온 signup_info:", signup_info) # 디버깅 출력
    if signup_info is None:
        return jsonify({'error': '회원 정보가 없습니다. 처음부터 다시 시작해주세요.'}), 400


    # 세션에서 정보 가져오기
    name = signup_info['Name']
    email = signup_info['Email_ID']
    phone = signup_info['PhoneNumber']
    hashed_password = signup_info['hashed_password']
   



    # DB 연결 및 커서 생성
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()


    # DB에 회원 정보 저장 로직
    insert_user_query = 'INSERT INTO member_user (Name, Email_ID, PhoneNumber) VALUES (%s, %s, %s)'
    cursor.execute(insert_user_query, (name, email, phone))
    member_no = cursor.lastrowid  # 새로 생성된 회원 번호 가져오기
    # 패스워드 해싱하여 저장
    insert_auth_query = 'INSERT INTO member_authenticationinfo (MemberNo, Password) VALUES (%s, %s)'
    cursor.execute(insert_auth_query, (member_no, hashed_password))  # 해싱된 패스워드 저장
        
    # 클라이언트에서 전달된 JSON 데이터 중에서 기업 정보 추출
    company_info = signup_info.get('company_info')
    if company_info is None:
        print("company_info is None!")  # 로그 확인
        return jsonify({'error': '회사 정보가 없습니다.'}), 400

    # 기업 정보 저장 쿼리
    insert_company_query = '''
    INSERT INTO member_company (BusinessRegistrationNumber, MemberNo, CompanyAddress, EstablishedDate, 
                                CEO, CompanySize, EmployeeCount, 
                                InterestKeywords)
    VALUES (%s, %s, %s, %s, 
            %s, %s, %s, 
            %s)
    '''
    cursor.execute(insert_company_query, 
                    (company_info['BusinessRegistrationNumber'], member_no, company_info['CompanyAddress'], 
                    company_info['EstablishedDate'], company_info['CEO'], company_info['CompanySize'], 
                    company_info['EmployeeCount'], company_info['InterestKeywords']
                    ))

    

    # 약관 동의 정보 추출
    agree_service = session.get('agree_service')
    agree_privacy = session.get('agree_privacy')
    agree_marketing = session.get('agree_marketing')

    # 약관 동의 정보 저장 쿼리
    insert_agreement_query = 'INSERT INTO agreement (MemberNo, AgreeService, AgreePrivacy, AgreeMarketing) VALUES (%s, %s, %s, %s)'
    cursor.execute(insert_agreement_query, (member_no, agree_service, agree_privacy, agree_marketing))

    conn.commit()

    cursor.close()
    conn.close()

    # 세션에서 회원 가입 정보 삭제
    session.pop('signup_info', None)
    session.pop('verified', None)
    session.pop('agree_service', None)
    session.pop('agree_privacy', None)
    session.pop('agree_marketing', None)

    return jsonify({'message': '회원가입이 완료되었습니다'}), 200



#---------------------------------이메일 인증-----------------------------------------------------------------

@app.route('/email_verification', methods=['POST'])
def email_verification():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['Email_ID']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    email = data['Email_ID']

    # 중복 이메일 확인
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM member_user WHERE Email_ID=%s", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': '이미 사용 중인 이메일입니다'}), 400
    cursor.close()
    conn.close()

    # 랜덤한 확인 코드 생성
    verification_code = generate_verification_code()

    # 생성된 코드를 세션에 저장
    session['verification_code'] = verification_code
    session['email'] = email
    
    # 이메일 전송
    send_verification_email(email, verification_code)

    return jsonify({'message': '인증 코드가 발송되었습니다', 'verification_code': verification_code}), 200






# ------------------------------------ID 찾기------------------------------------------------------------------------------------------------

# 인증번호 요청
@app.route('/ID_find/email', methods=['POST'])
def id_find():
    data = request.get_json()
    email = data.get('Email_ID')

    # Check if email exists in the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(buffered=True)
    
    cursor.execute("SELECT 1 FROM member_user WHERE Email_ID=%s", (email,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': '해당 이메일로 가입된 계정이 없습니다'}), 400  # 변경된 부분

    # Generate verification code
    verification_code = generate_verification_code()

    # Save email and verification code to session
    session['email'] = email
    session['verification_code'] = verification_code

    # Send verification email
    send_verification_email(email, verification_code)

    return jsonify({'message': '인증 코드가 메일로 발송되었습니다'}), 200


@app.route('/ID_find/verify', methods=['POST'])
def verify_code_and_get_id():
    try:
        email = session.get('email')
        server_code = session.get('verification_code')

        if email is None or server_code is None:
            return jsonify({"error": "이메일 또는 인증 코드 정보가 없습니다. 인증 코드 요청부터 다시 시작해주세요."}), 400

        user_code = request.json.get('code')
        if not email or not user_code:
            return jsonify({"error": "이메일과 인증 코드는 필수입니다"}), 400

        if user_code != server_code:
            return jsonify({"error": "인증 코드가 일치하지 않습니다"}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT Email_ID FROM member_user WHERE Email_ID=%s", (email,))
        user_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        # 세션에서 이메일과 인증 코드 정보 삭제
        for key in ['email', 'verification_code']:
            session.pop(key, None)
        return jsonify({"user_id": user_id, "message": "인증 성공. 당신의 ID입니다."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
#---------------------------------------------- 비밀번호찾기 / 재설정 ---------------------------------------------------------------

# 비밀번호 재설정 코드 요청
@app.route('/password_reset/request_code', methods=['POST'])
def request_password_reset_code():
    try:
        email = request.json.get('Email_ID')
        if not email:
            return jsonify({"error": "이메일 입력은 필수입니다."}), 400

        # 랜덤한 확인 코드 생성
        verification_code = generate_verification_code()

        # 생성된 코드를 세션에 저장
        session['verification_code'] = verification_code
        session['email'] = email

        # 이메일 전송
        send_verification_email(email, verification_code)

        return jsonify({"message": "인증 코드가 발송되었습니다"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/password_reset/verify_and_reset', methods=['POST'])
def verify_code_and_reset_password():
    try:
        email = session.get('email')
        server_code = session.get('verification_code')
        user_code = request.json.get('code')
        new_password = request.json.get('new_password')
        new_password_confirm = request.json.get('new_password_confirm')

        if email is None or server_code is None:
            return jsonify({"error": "이메일 또는 인증 코드 정보가 없습니다. 인증 코드 요청부터 다시 시작해주세요."}), 400

        if not user_code or not new_password or not new_password_confirm:
            return jsonify({"error": "인증 코드, 새로운 비밀번호, 비밀번호 확인은 필수입니다"}), 400

        if new_password != new_password_confirm:
            return jsonify({"error": "새 비밀번호가 일치하지 않습니다"}), 400

        if user_code != server_code:
            return jsonify({"error": "인증 코드가 일치하지 않습니다"}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)

        # 비밀번호 해싱
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("UPDATE member_authenticationinfo SET Password=%s WHERE Email_ID=%s", (hashed_password, email))
        conn.commit()
        cursor.close()
        conn.close()

        # 세션에서 이메일과 인증 코드 정보 삭제
        for key in ['email', 'verification_code']:
            session.pop(key, None)

        return jsonify({"message": "비밀번호가 성공적으로 재설정되었습니다."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500





#---------------------------------------로그인-------------------------------------------------------------------

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
#-------------------------------------접근제한-----------------------------------------------------------------


# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if session.get('user_id') is None:
#             return jsonify({'error': '로그인이 필요합니다'}), 401
#         return f(*args, **kwargs)
#     return decorated_function



#-------------------------------------------------------------- 로그아웃-------------------------------------------------------------

@app.route('/logout', methods=['POST'])
def logout():
    # 세션에서 사용자 ID 제거
    session.pop('user_id', None)

    return jsonify({'message': '로그아웃 성공'}), 200

#-----------------------------------------------------회원정보 변경------------------------------------------------------------------


@app.route('/update_profile', methods=['POST'])
# @login_required
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
post_lists_api = api.namespace('공고조회', description='공고조회 API')
member_model = api.model('member_model', {
    'MemberNo': fields.Integer(required=True, description='회원 고유 번호')
})
@post_lists_api.route('/post/lists')
class get_post_list(Resource):
    @api.expect(member_model, validate=True)
    def post(self):
        data = api.payload
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

download_attachment_api = api.namespace('첨부파일다운로드', description='첨부파일 다운로드 API')
download_model = api.model('download_model', {
    'PostID': fields.Integer(required=True, description='문서 고유번호'),
    'pfi_originname': fields.String(required=True, description='원본 파일명')
})
@download_attachment_api.route('/post/lists/download')
class download_attachment(Resource):
    @api.expect(download_model, validate=True)
    def post(self):
        data = api.payload
        PostID = data['PostID']
        pfi_originname = data['pfi_originname']
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

bookmark_insert_api = api.namespace('즐겨찾기추가', description='즐겨찾기 추가 API')
bookmark_model = api.model('bookmark_model', {
    'MemberNo': fields.Integer(required=True, description='회원 고유 번호'),
    'PostID': fields.Integer(required=True, description='문서 고유번호')
})
@bookmark_insert_api.route('/post/bookmark/insert')
class insert_bookmark(Resource):
    @api.expect(bookmark_model, validate=True)
    def post(self):
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        data = api.payload
        MemberNo = data.get('MemberNo')
        PostID = data.get('PostID')
        sql = "INSERT INTO BOOKMARK (MemberNo, PostID) VALUES (%s, %s)"

        cursor.execute(sql, (MemberNo, PostID))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"result": "success", "description":"즐겨찾기 추가 성공"})

bookmark_delete_api = api.namespace('즐겨찾기삭제', description='즐겨찾기 삭제 API')
bookmark_model = api.model('bookmark_model', {
    'MemberNo': fields.Integer(required=True, description='회원 고유 번호'),
    'PostID': fields.Integer(required=True, description='문서 고유번호')
})
@bookmark_delete_api.route('/post/bookmark/delete')
class delete_bookmark(Resource):
    @api.expect(bookmark_model, validate=True)
    def delete(self):
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

post_recommend_api = api.namespace('AI맞춤추천공고', description='AI 맞춤 추천 공고 API')
@post_recommend_api.route('/post/lists/recommend')
class get_post_recommend_list(Resource):
    @api.expect(member_model, validate=True)
    def post(self):
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

post_bookmark_api = api.namespace('즐겨찾기목록', description='즐겨찾기 목록 API')
@post_bookmark_api.route('/post/lists/bookmark')
class get_post_bookmark_list(Resource):
    @api.expect(member_model, validate=True)
    def post(self):
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        data = api.payload
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

post_api = api.namespace('공고상세보기', description='공고 상세보기 API')
@post_api.route('/post/lists/<int:PostID>')
class get_post(Resource):
    def get(self, PostID):
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

search_api = api.namespace('검색', description='검색 API')
search_model = api.model('search_model', {
    'MemberNo': fields.Integer(required=True, description='회원 고유 번호'),
    'department': fields.String(required=False, description='지역 검색 [서울특별시, 경기도, 인천광역시, 강원도, 충청남도, 대전광역시, 충청북도, 세종특별자치시, 부산광역시, 울산광역시, 대구광역시, 경상북도, 경상남도, 전라남도, 광주광역시, 전라북도, 제주특별자치도, 중앙부처]'),
    'company': fields.String(required=False, description='대상 기업 [중소기업, 벤처기업, 소상공인, 사회적기업, 여성기업, 장애인기업]'),
    'supportType': fields.String(required=False, description='인력 충원 형태 [일반, 청년, 여성, 장애인]'),
    'part': fields.String(required=False, description='분야 [금융, 기술, 인력, 수출, 내수, 창업, 경영, 기타]'),
    'postDateYN': fields.String(required=False, description='필터 검색 시 사용하는 날짜 기준 [Y, N] (기본값: Y)'),
    'startDate': fields.String(required=False, description='시작 날짜 포맷: yyyy-mm-dd'),
    'endDate': fields.String(required=False, description='종료 날짜 포맷: yyyy-mm-dd'),
    'registerClosingYN': fields.String(required=False, description='접수 마감건 문서 제외 여부 [Y, N] (기본값: Y)'),
    'bookmarkPageYN': fields.String(required=False, description='즐겨찾기 페이지 여부 [Y,N] (기본값: N)'),
})
@search_api.route('/post/lists/search')
class get_search_post_list(Resource):
    @api.expect(search_model, validate=True)
    def post(self):
        data = api.payload
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
















