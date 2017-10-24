#!/usr/bin/python2
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import hmac
import hashlib
import os
import sys

# Local imports
from dbg import pr
import gitcmd
import runner

app = Flask(__name__)

def do_pull_request(jpl):

    # Commit origin
    pr(gitcmd.git_branch(jpl))
    pr(gitcmd.git_remote_string(jpl))
    pr(gitcmd.git_checkout_cmd(jpl))
    

def verify_hmac_hash(data, signature):
    github_secret = os.environ['GITHUB_SECRET']
    mac = hmac.new(github_secret, msg=data, digestmod=hashlib.sha1)
    return hmac.compare_digest('sha1=' + mac.hexdigest(), signature)

@app.route('/')
def hello_world():
    return 'Hello World2!'

@app.route('/job/<git>/<int:job_id>')
def show_post(git, job_id):
    # show the post with the given id, the id is an integer
    with open('pull_request.json', 'r') as f:
        jpl = json.load(f)

    runner.add_job(jpl)
    return 'OK'

@app.route('/payload', methods=['POST'])
def payload():
    signature = request.headers.get('X-Hub-Signature')
    data = request.data
    #f = open('pull_request.json', 'w')
    #payload = request.get_json()
    #json.dump(payload, f, indent=4)
    #f.close()
    return 'foo'
    #if verify_hmac_hash(data, signature) is not True:
    #    return jsonify({'msg': 'wrong signature'})

    if request.headers.get('X-GitHub-Event') == "pull_request":
        payload = request.get_json()
        response = do_pull_request(payload)
    return 'Got payload'



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')