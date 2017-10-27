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

    # Need to convert this to unicode, since hmac.compare_digest expect either a
    # unicode string or a byte array
    hexdigest = unicode("sha1=" + mac.hexdigest(), "utf-8")
    return hmac.compare_digest(hexdigest, signature)


def dump_json_blob_to_file(request, filename="last_blob.json"):
    """ Debug function to dump the last json blob to file """
    f = open(filename, 'w')
    payload = request.get_json()
    json.dump(payload, f, indent=4)
    f.close()


@app.route('/')
def hello_world():
    return 'OP-TEE automatic tester!'

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
    dump_json_blob_to_file(request)

    # Check the signature to ensure that the message comes from GitHub
    if verify_hmac_hash(data, signature) is not True:
        return jsonify({'msg': 'wrong signature'})

    if request.headers.get('X-GitHub-Event') == "pull_request":
        payload = request.get_json()
        response = runner.add_job(payload)
    return 'Got payload'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
