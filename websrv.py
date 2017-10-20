#!/usr/bin/python2
from __future__ import print_function
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import hmac
import hashlib
import os
import sys

app = Flask(__name__)

job = {}

def pr(s):
    print(s, file=sys.stderr)

def get_checkout_cmd(co):
    return "git reset --hard " + co['sha']

def get_remote_string(co):
    return "git remote add commiter https://github.com/" + co['full_name']

def get_commit_and_origin(jpl):
    full_name = jpl['pull_request']['head']['repo']['full_name']
    ref = jpl['pull_request']['head']['ref']
    sha = jpl['pull_request']['head']['sha']
    return {'full_name': full_name, 'ref': ref, 'sha': sha}


def do_pull_request(jpl):
    number = jpl['number']

    # Commit origin
    co = get_commit_and_origin(jpl)
    pr("full_name: %s, ref: %s, sha: %s" % (co['full_name'], co['ref'], co['sha']))
    pr(get_remote_string(co))
    pr(get_checkout_cmd(co))
    

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
        data = json.load(f)

    do_pull_request(data)
    return '%s : %d' % (git, job_id)

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
