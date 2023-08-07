# app.py

from flask import Flask, url_for

app = Flask(__name__)

@app.route('/')
def index():
    user_profile_url = url_for('user_profile', username='johndoe')
    return f'홈페이지입니다. <a href="{user_profile_url}">John Doe의 프로필로 이동</a>'

@app.route('/user/<username>')
def user_profile(username):
    return f'{username}의 프로필 페이지입니다!'

if __name__ == '__main__':
    app.run(debug=True)
