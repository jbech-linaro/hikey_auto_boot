#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for, jsonify
import hashlib
import hmac
import json
import logging as log
import os
import sys

# Local imports
from dbg import pr
import cfg
import logger
import worker

app = Flask(__name__)

def verify_hmac_hash(data, signature):
    github_secret = bytearray(os.environ['GITHUB_SECRET'], 'utf-8')
    mac = hmac.new(github_secret, msg=data, digestmod=hashlib.sha1)

    # Need to convert this to bytearray, since hmac.compare_digest expect either
    # a unicode string or a byte array
    hexdigest = bytearray("sha1=" + mac.hexdigest(), "utf-8")
    signature = bytearray(signature, "utf-8")
    return hmac.compare_digest(hexdigest, signature)


def dump_json_blob_to_file(request, filename="last_blob.json"):
    """ Debug function to dump the last json blob to file """
    with open(filename, 'w') as f:
        payload = request.get_json()
        json.dump(payload, f, indent=4)

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
    return log

@app.route('/')
def main_page(page=1):
    sql_data = worker.db_get_html_row(page)
    return render_template('main.html', sd=sql_data, page=page)

@app.route('/<int:page>')
def main_paginate(page):
    sql_data = worker.db_get_html_row(page)
    return render_template('main.html', sd=sql_data, page=page)


@app.route('/restart/<int:pr_id>/<pr_sha1>')
def restart_page(pr_id, pr_sha1):
    worker.user_add(pr_id, pr_sha1)
    return 'OK'

@app.route('/stop/<int:pr_id>/<pr_sha1>')
def stop_page(pr_id, pr_sha1):
    worker.cancel(pr_id, pr_sha1)
    return 'OK'

@app.route('/<git_name>/<int:github_nbr>')
def show_post(git_name, github_nbr):
    # show the post for a build job
    bl = read_log(git_name, github_nbr, cfg.build_log)

    fl = read_log(git_name, github_nbr, cfg.flash_log)

    tl = read_log(git_name, github_nbr, cfg.run_log)

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
        worker.add(payload)
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
