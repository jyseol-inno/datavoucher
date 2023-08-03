from flask import Flask
from flask_restx import Api, Resource  # flask_restplus 대신 flask_restx를 사용

app = Flask(__name__)
api = Api(app)

@api.route('/hello')
class HelloWorld(Resource):
    def get(self):
        return {'message': 'hello world'}

if __name__ == '__main__':
    app.run(debug=True)
