#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging as log
import json
import threading
import time
import os
import random
import sqlite3
from collections import deque

################################################################################
# SQLITE3
################################################################################
DB_FILE = os.path.join(os.path.dirname(__file__), 'hab.db')

def db_connect(db_file=DB_FILE):  
    con = sqlite3.connect(db_file)
    return con

def initialize_db():
    if not os.path.isfile(DB_FILE):
        con = db_connect()
        cur = con.cursor()
        sql = '''
                CREATE TABLE job (
                    id integer PRIMARY KEY,
                    pr_id text NOT NULL,
                    pr_number text NOT NULL,
                    full_name text NOT_NULL,
                    date text NOT NULL,
                    run_time text DEFAULT "00:00",
                    status text DEFAULT Pending)
              '''
        cur.execute(sql)
        con.close()

def db_add_build_record(pr_id, pr_number, full_name):
    con = db_connect()
    cur = con.cursor()
    sql = "INSERT INTO job (pr_id, pr_number, full_name, date) " + \
            "VALUES('{}','{}','{}',datetime('now'))".format(
                    pr_id, pr_number, full_name)
    log.debug(sql)
    cur.execute(sql)
    con.commit()
    con.close()

def db_get_html_row():
    con = db_connect()
    cur = con.cursor()
    #sql = "SELECT * FROM job"
    sql = "SELECT * FROM job ORDER BY id DESC LIMIT 3"
    cur.execute(sql)
    r = cur.fetchall()
    con.commit()
    con.close()
    return r

################################################################################
# GitHub Json
################################################################################
class Singleton(type):
    instance = None
    def __call__(cls, *args, **kw):
        if not cls.instance:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance

GITHUB = "https://github.com"

gh = None
class GitHub(metaclass=Singleton):
    def __init__(self, payload):
        self._payload = payload # JSON payload

    def pr_id(self):
        """Returns the ID of the GitHub job."""
        return self._payload['pull_request']['id']

    def pr_number(self):
        """Returns the pull request number."""
        return self._payload['number']

    def pr_sha1(self):
        """Returns the commit hash (the SHA-1)."""
        return self._payload['pull_request']['head']['sha']

    def pr_clone_url(self):
        """Returns full URL to the committers own project."""
        return self._payload['pull_request']['head']['repo']['clone_url']

    def pr_name(self):
        """Returns the name (ex. optee_os) of the Git project."""
        return self._payload['repository']['name']

    def pr_full_name(self):
        """Returns the full name (ex. OP-TEE/optee_os) of the Git project."""
        return self._payload['repository']['full_name']

def initialize_github(payload=None):
    global gh
    if payload is not None:
        gh = GitHub(payload)

################################################################################
# Jobs
################################################################################
class Job():
    """Class defining a complete Job which normally includes clone, build, flash
    and run tests on a device."""
    def __init__(self, pr_number, payload):
        self.payload = payload
        self.gh = GitHub(payload)

    def __str__(self):
        return "{}".format(self.pr_number())

    def pr_number(self):
        return self.gh.pr_number()

    def pr_id(self):
        return self.gh.pr_id()

    def pr_full_name(self):
        return self.gh.pr_full_name()

class JobThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
regularly for the stopped() condition."""

    def __init__(self, job):
        super(JobThread, self).__init__()
        self._stop_event = threading.Event()
        self.job = job

    def stop(self):
        log.debug("Stopping PR {}".format(self.job.pr_number()))
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        """This is the main function for running a complete clone, build, flash
        and test job."""
        log.debug("START Job : {}".format(self.job))
        for i in range(0, 10):
            time.sleep(1)
            pr_id = self.job.pr_id()
            pr_number = self.job.pr_number()
            pr_full_name = self.job.pr_full_name()

            db_add_build_record(pr_id, pr_number, pr_full_name)

            if self.stopped():
                log.debug("STOP Job : {}[{}]".format(self.job, i))
                return
        log.debug("END   Job : {}".format(self.job))

################################################################################
# Worker
################################################################################
worker_thread = None

class WorkerThread(threading.Thread):
    """Thread class responsible to adding and running jobs."""
    def __init__(self, group=None, target=None, name=None,
            args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.q = deque()
        self.job_dict = {}
        self.jt = None
        return

    def add(self, pr_number, payload=None):
        """Responsible of adding new jobs the the job queue."""
        # Remove pending jobs affecting same PR from the queue
        while self.q.count(pr_number) > 0:
            log.debug("PR{} pending, removing it from queue".format(pr_number))
            self.q.remove(pr_number)

        # If the ongoing work is from the same PR, then stop that too
        if self.jt is not None:
            if self.jt.job.pr_number() == pr_number:
                log.debug("The new/updated PR ({}) have a corresponding job running, sending stop()".format(pr_number))
                self.jt.stop()

        # Finally add the new/updated PR to the queue (PR number to the queue
        # and store the corresponding payload in a dictionary).
        self.job_dict[pr_number] = payload
        self.q.append(pr_number)
        log.info("Added PR{}".format(pr_number))

    def cancel(self, pr_number):
        if self.jt is not None:
            if self.jt.job.pr == pr_number:
                log.debug("Got a stop from web PR ({})".format(pr))
                self.jt.stop()

    def force_restart(self, pr_number, pr_id=None):
        # If there is already a job ongoing, then cancel it. Note that doing
        # like this comes with limitations, since this could stop a job start
        # has been started by a real pull request. This should be fixed in a
        # nicer way in the future. One way could be to check the pr_id here also
        # and not just the pr_number.
        if self.jt is not None:
            if self.jt.job.pr == pr_number:
                log.debug("Got a stop from web PR ({})".format(pr))
                self.jt.stop()

        # TODO: Add payload!
        self.add(pr_number)

    def run(self):
        """Main function taking care of running all jobs in the job queue."""
        while(True):
            time.sleep(3)
            log.debug("Checking for work (q:{})".format(self.q))

            if len(self.q) > 0:
                pr = self.q.popleft()
                payload = self.job_dict[pr]
                log.debug("Handling job: {}".format(pr))
                self.jt = JobThread(Job(pr, payload))
                self.jt.start()
                self.jt.join()
                self.jt = None
        return

def initialize_worker_thread():
    """Initialize the main thread responsible for adding and running jobs."""
    global worker_thread
    # Return if thread is already running.
    if worker_thread != None:
        return

    worker_thread = WorkerThread()
    worker_thread.setDaemon(True)
    worker_thread.start()
    log.info("Worker thread has been started")

################################################################################
# Logger
################################################################################
def initialize_logger():
    LOG_FMT = "[%(levelname)s] %(filename)-16s%(funcName)s():%(lineno)d # %(message)s"
    log.basicConfig(#filename=cfg.core_log,
        level = log.DEBUG,
        format = LOG_FMT,
        filemode = 'w')


################################################################################
# Main
################################################################################
initialized = False

def initialize(payload):
    global initialized

    if not initialized:
        initialize_logger()
        initialize_worker_thread()
        initialize_github(payload)
        initialize_db()
        log.info("Initialize done!")
        initialized = True

def add(payload, debug=False):
    initialize(payload)

    if payload is None:
        l.error("Cannot add job without payload")
        return False

    global gh
    pr = gh.pr_number()

    # This is basically just for testing
    if debug:
        log.debug("Add debug job")
        debug_test(pr, payload)
    else:
        worker_thread.add(pr, payload)
    return True

def cancel(pr_number):
    if pr_number is None:
        log.error("Trying to stop a job without a PR number")
    elif worker_thread is None:
        log.error("Threads are not initialized")
    else:
        worker_thread.cancel(pr_number)

def force_restart(pr_number):
    if pr_number is None:
        log.error("Trying to stop a job without a PR number")
    elif worker_thread is None:
        log.error("Threads are not initialized")
    else:
        worker_thread.force_restart(pr_number)

################################################################################
# Debug
################################################################################
def debug_test(pr_number, payload):
    for j in range(0, 5):
        worker_thread.add(pr_number, payload)

    while (True):
        pr = random.randint(0, 5)
        worker_thread.add(pr_number + pr, payload)
        time.sleep(random.randint(1, 2))

def load_payload_from_file(filename=None):
    fname = 'last_blob.json'
    payload = None

    if filename is not None:
        fname = filename

    with open('last_blob.json', 'r') as f:
        payload = f.read()

    # Convert it back to the same format as we get from websrv.py (from human
    # readable to Python data structure).
    return json.loads(payload)

def local_run():
    add(load_payload_from_file(), True)
    time.sleep(1)
    add(load_payload_from_file(), True)
    time.sleep(1)
    add(load_payload_from_file(), True)
    time.sleep(1)
    add(load_payload_from_file(), True)

if __name__ == "__main__":
    local_run()
    worker_thread.join()
