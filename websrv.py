#!/usr/bin/python2
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World2!'

@app.route('/build/<int:post_id>')
def show_post(post_id):
    # show the post with the given id, the id is an integer
            return 'Post %d' % post_id

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
