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
import logger
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

def read_log(git_name, github_nbr, filename):
    log_file_dir = "{}/logs/{name}/{nbr}".format(os.getcwd(),
            name=git_name, nbr=github_nbr)
    # TODO: Check for "../" in log_file_dir so we are not vulnerable to
    # injection attacks.
    log_file = "{d}/{f}".format(d=log_file_dir, f=filename)
    log = ""
    try:
        with open(log_file, 'r') as f:
            log = f.read()
    except IOError:
        pass

    # Must decode to UTF otherwise there is a risk for a UnicodeDecodeError
    # exception when trying to access the log from the web-browser.
    return log.decode('utf-8')


@app.route('/')
def hello_world():
    return 'OP-TEE automatic tester!'

@app.route('/<git_name>/<int:github_nbr>')
def show_post(git_name, github_nbr):
    # show the post for a build job

    print(git_name)
    bl = read_log(git_name, github_nbr, "build.log")

    fl = read_log(git_name, github_nbr, "flash.log")

    tl = read_log(git_name, github_nbr, "xtest.log")

    return render_template('job.html', gn=git_name, gnr=github_nbr,
            build_log=bl, flash_log=fl, test_log=tl)

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
        runner.add_job(payload)
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
