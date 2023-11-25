import boto3
from flask_cors import CORS

from flask import Flask, jsonify

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/test1'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret key'
CORS(app)
s3 = boto3.client('s3',
    aws_access_key_id="AKIAVDWNEKJDPVUDCWD7",
    aws_secret_access_key="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",
    region_name="ap-northeast-2"
)


@app.route('/')
def home():
    return jsonify({'message': 'Hello World!'}), 200


if __name__ == '__main__':
    from src import api

    app.register_blueprint(api)
    app.run(host='0.0.0.0', port=5001, debug=True)
