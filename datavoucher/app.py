from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/hello", methods=['GET'])
def hello():
  return "hello world bro"

@app.route("/signup",methods=['POST'])
def sign_up():
    user = request.json
    response = {
        'name': user['name'],
        'email': user['email'],
        'password': user['password'],
        'profile': user['profile']
    }
    return jsonify(response), 200

if __name__ == "__main__":
  app.run(port=8000)



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
  return "hello world bro"

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