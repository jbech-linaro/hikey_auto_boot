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

@app.route('/')
def main_page(page=1):
    sql_data = worker.db_get_html_row(page)
    return render_template('main.html', sd=sql_data, page=page)

@app.route('/<int:page>')
def main_paginate(page):
    sql_data = worker.db_get_html_row(page)
    return render_template('main.html', sd=sql_data, page=page)

# TODO: This will show PRs from all gits and not a unique git
@app.route('/pr/<int:pr_number>')
def show_pr(pr_number):
    sql_data = worker.db_get_pr(pr_number)
    return render_template('pr.html', sd=sql_data, pr_number=pr_number)

@app.route('/restart/<int:pr_id>/<pr_sha1>')
def restart_page(pr_id, pr_sha1):
    worker.user_add(pr_id, pr_sha1)
    return 'OK'

@app.route('/stop/<int:pr_id>/<pr_sha1>')
def stop_page(pr_id, pr_sha1):
    worker.cancel(pr_id, pr_sha1)
    return 'OK'

# logs/jbech-linaro/optee_os/2/149713049/2bcfbd494fd4ce795840697a4d10cdb26f39d6aa
@app.route('/logs/<owner>/<project>/<int:pr_number>/<int:pr_id>/<pr_sha1>')
def show_log(owner, project, pr_number, pr_id, pr_sha1):
    pr_full_name = "{}/{}".format(owner, project)
    logs = worker.get_logs(pr_full_name, pr_number, pr_id, pr_sha1)
    return render_template('job.html', pr_full_name=pr_full_name,
            pr_number=pr_number, pr_id=pr_id, pr_sha1=pr_sha1, logs=logs)

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
    worker.initialize()
    app.run(debug=True, host='0.0.0.0')
