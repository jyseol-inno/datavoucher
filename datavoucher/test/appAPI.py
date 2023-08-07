
from flask import Flask, request, jsonify

app = Flask(__name__)

# 가상의 데이터베이스 역할을 하는 리스트 생성
users = []


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    # 필수 필드 확인
    if 'name' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'error': '모든 필드를 입력해주세요'}), 400

    name = data['name']
    email = data['email']
    password = data['password']

    print(name)
    print(email)
    print(password)

    # 이메일 중복 확인
    if any(user['email'] == email for user in users):
        return jsonify({'error': '이미 가입된 이메일입니다'}), 409

    # 회원가입 정보 저장
    user = {
        'name': name,
        'email': email,
        'password': password
    }
    users.append(user)
    print(users)
    return jsonify({'message': '회원가입이 완료되었습니다'}), 201


if __name__ == '__main__':
    app.run(debug=True)
