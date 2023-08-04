from flask import Flask, request, jsonify, session
from flask_session import Session  # 서버 측 세션을 위한 Flask-Session 추가
import mysql.connector

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  # 세션 데이터를 파일 시스템에 저장
Session(app)  # 앱에 세션 설정 적용




# MariaDB 연결 정보
db_config = {
    'host': 'localhost',
    'user': 'root',     # 사용자 이름에 맞게 변경해주세요
    'password': 'root', # 비밀번호에 맞게 변경해주세요
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

@app.route('/')
def index():
    session['key'] = 'value'
    return 'hi'


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



@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['Name', 'Password', 'PhoneNumber', 
                       'BusinessRegistrationNumber', 'CompanyName', 'CompanyAddress', 
                       'CompanyPhoneNumber', 'Industry', 'EstablishedDate', 'CEO', 'CompanySize']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    name = data['Name']
    password = data['Password']
    phone = data['PhoneNumber']

    company_info = {
        'BusinessRegistrationNumber': data['BusinessRegistrationNumber'],
        'CompanyName': data['CompanyName'],
        'CompanyAddress': data['CompanyAddress'],
        'CompanyPhoneNumber': data['CompanyPhoneNumber'],
        'Industry': data['Industry'],
        'EstablishedDate': data['EstablishedDate'],
        'CEO': data['CEO'],
        'CompanySize': data['CompanySize']
    }

    # 세션에서 이메일과 약관 동의 정보 가져오기
    email = session.get('email')
    agree_service = session.get('agree_service')
    agree_privacy = session.get('agree_privacy')
    agree_marketing = session.get('agree_marketing')
    verified = session.get('verified')

    if not all([email, agree_service, agree_privacy, verified]):
        return jsonify({'error': '이메일 인증과 약관 동의를 먼저 완료해주세요'}), 400

    # 나머지 코드는 동일...

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
        INSERT INTO member_company (BusinessRegistrationNumber, CompanyName, MemberNo, 
                                    CompanyAddress, CompanyPhoneNumber, Industry, EstablishedDate, CEO, CompanySize)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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

if __name__ == '__main__':
    app.run(debug=True)
















'''
세션을 이용해서 엔드포인트 분리
@app.route('/agreement', methods=['POST'])
def agreement():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['HomeUseAgreement', 'PersonalInfoAgreement', 'MarketingAgreement']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    # 약관 동의 정보를 세션에 저장
    for field in required_fields:
        session[field] = data[field]

    return jsonify({'message': '약관 동의 정보가 저장되었습니다'}), 201

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    # 필수 필드 확인
    required_fields = ['Name', 'Email_ID', 'Password', 'PhoneNumber']
    if not all(field in data for field in required_fields):
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    # 본인 인증 정보와 회원 정보를 데이터베이스에 저장하는 코드...
    # ...


'''