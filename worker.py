#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging as log
import json
import threading
import time
import os
import random
import signal
import sqlite3
import sys

import github

################################################################################
# Sigint
################################################################################
def signal_handler(signal, frame):
    log.debug("Gracefully killed!")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pr_id text NOT NULL,
                    pr_number text NOT NULL,
                    full_name text NOT_NULL,
                    sha1 text NOT_NULL,
                    date text NOT NULL,
                    run_time text DEFAULT "N/A",
                    status text DEFAULT Pending,
                    payload text NOT NULL)
              '''
        cur.execute(sql)
        con.commit()
        con.close()

def db_add_build_record(payload):
    pr_id = github.pr_id(payload)
    pr_sha1 = github.pr_sha1(payload)

    log.debug("Adding record for {}/{}".format(pr_id, pr_sha1))
    if pr_id == 0 or pr_sha1 == 0:
        log.error("Trying to add s record with no pr_id or pr_sha1!")
        return

    con = db_connect()
    cur = con.cursor()
    sql = "SELECT pr_id FROM job WHERE pr_id = '{}' AND sha1 = '{}'".format(pr_id, pr_sha1)
    cur.execute(sql)
    r = cur.fetchall()
    if len(r) >= 1:
        log.debug("Record for pr_id/sha1 {}/{} is already in the "
                "database".format(pr_id, pr_sha1))
        con.commit()
        con.close()
        return

    pr_number = github.pr_number(payload)
    pr_full_name = github.pr_full_name(payload)
    sql = "INSERT INTO job (pr_id, pr_number, full_name, sha1, date, payload) " + \
            "VALUES('{}','{}','{}', '{}', datetime('now'), '{}')".format(
                    pr_id, pr_number, pr_full_name, pr_sha1, json.dumps(payload))
    cur.execute(sql)
    con.commit()
    con.close()

def db_update_job(pr_id, pr_sha1, status, running_time):
    log.debug("Update record for {}/{}".format(pr_id, pr_sha1))
    con = db_connect()
    cur = con.cursor()
    sql = "UPDATE job SET status = '{}', run_time = '{}', date = datetime('now') WHERE pr_id = '{}' AND sha1 = '{}'".format(
                    status, running_time, pr_id, pr_sha1)
    cur.execute(sql)
    con.commit()
    con.close()

def db_get_payload_from_pr_id(pr_id, pr_sha1):
    con = db_connect()
    cur = con.cursor()
    sql = "SELECT payload FROM job WHERE pr_id = '{}' AND sha1 = '{}'".format(pr_id, pr_sha1)
    cur.execute(sql)
    r = cur.fetchall()
    if len(r) > 1:
        log.error("Found duplicated pr_id/pr_sha1 in the database")
        return -1
    con.commit()
    con.close()
    return json.loads("".join(r[0]))
    

def db_get_html_row(page):
    con = db_connect()
    cur = con.cursor()
    sql = "SELECT * FROM job ORDER BY id DESC LIMIT {}".format(page * 15)
    cur.execute(sql)
    r = cur.fetchall()
    con.commit()
    con.close()
    return r

################################################################################
# Utils
################################################################################
def get_running_time(time_start):
    """Returns the running time on format: <hours>h:<minutes>m:<seconds>s."""
    m, s = divmod(time.time() - time_start, 60)
    h, m = divmod(m, 60)
    return "{}h:{:02d}m:{:02d}s".format(int(h), int(m), int(s))

################################################################################
# Jobs
################################################################################
class Job():
    """Class defining a complete Job which normally includes clone, build, flash
    and run tests on a device."""
    def __init__(self, payload, user_initiated=False):
        self.payload = payload
        self.user_initiated = user_initiated
        self.status = "Pending"

    def __str__(self):
        return "{}:{}/{}".format(
                self.pr_id(),
                self.pr_full_name(),
                self.pr_number())

    def pr_number(self):
        return github.pr_number(self.payload)

    def pr_id(self):
        return github.pr_id(self.payload)

    def pr_full_name(self):
        return github.pr_full_name(self.payload)

    def pr_sha1(self):
        return github.pr_sha1(self.payload)

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
        time_start = time.time()

        # 1. Insert initial record in the database
        pr_id = self.job.pr_id()
        pr_sha1 = self.job.pr_sha1()
        # This will fail when running with test data, since there is the unique
        # constrain in the database.
        db_add_build_record(self.job.payload)
        db_update_job(pr_id, pr_sha1, "Running", "N/A")

        # 2. Run (fake) job
        for i in range(0, random.randint(0, 1000)):
            time.sleep(random.randint(0, 10))
            if self.stopped():
                log.debug("STOP Job : {}[{}]".format(self.job, i))
                running_time = get_running_time(time_start)
                db_update_job(pr_id, pr_sha1, "Cancelled(R)", running_time)
                return
            log.debug("RUNNING Job : {}[{}]".format(self.job, i))
        running_time = get_running_time(time_start)
        log.debug("END   Job : {} --> {}".format(self.job, running_time))
        db_update_job(pr_id, pr_sha1, "Success", running_time)

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
        self.q = []
        self.job_dict = {}
        self.jt = None
        self.lock = threading.Lock()

    def user_add(self, pr_id, pr_sha1):
        if pr_id is None or pr_sha1 is None:
            log.error("Missing pr_id or pr_sha1 when trying to submit user job")
            return

        with self.lock:
            log.info("Got user initiated add {}/{}".format(pr_id, pr_sha1))
            payload = db_get_payload_from_pr_id(pr_id, pr_sha1)
            if payload is None:
                log.error("Didn't find payload for ID:{}".format(pr_id))
                return

            self.q.append(pr_id)
            self.job_dict[pr_id] = Job(payload, True)
            db_update_job(pr_id, pr_sha1, "Pending", "N/A")

    def add(self, payload):
        """Responsible of adding new jobs the the job queue."""
        if payload is None:
            log.error("Missing payload when trying to add job")
            return

        pr_id = github.pr_id(payload)
        pr_number = github.pr_number(payload)
        pr_sha1 = github.pr_sha1(payload)

        with self.lock:
            log.info("Got GitHub initiated add {}/{} --> PR#{}".format(pr_id, pr_sha1, pr_number))
            # Check whether the jobs in the current queue touches the same PR
            # number as this incoming request does.
            for i, elem in enumerate(self.q):
                job_in_queue = self.job_dict[elem]
                # Remove existing jobs as long as they are not user initiated
                # jobs.
                if (job_in_queue.pr_number() == pr_number):
                    if not job_in_queue.user_initiated:
                        log.debug("Non user initiated job found in queue, removing {}".format(elem))
                        del self.q[i]

            # Check whether current job also should be stopped (i.e, same
            # PR, but _not_ user initiated).
            if self.jt is not None and self.jt.job.pr_number() == pr_number \
                and not self.jt.job.user_initiated:
                    log.debug("Non user initiated job found running, stopping {}".format(self.jt.job))
                    self.jt.stop()

            self.q.append(pr_id)
            self.job_dict[pr_id] = Job(payload, False)

    def cancel(self, pr_id, pr_sha1):
        force_update = True

        # Stop pending jobs
        for i, elem in enumerate(self.q):
            job_in_queue = self.job_dict[elem]
            if job_in_queue.pr_id() == pr_id and job_in_queue.pr_sha1() == pr_sha1:
                log.debug("Got a stop from web {}/{}".format(pr_id, pr_sha1))
                del self.q[i]
                db_update_job(job_in_queue.pr_id(), job_in_queue.pr_sha1(), "Cancelled(Q)", "N/A")
                force_update = False

        # Stop the running job
        if self.jt is not None:
            if self.jt.job.pr_id() == pr_id and self.jt.job.pr_sha1() == pr_sha1:
                log.debug("Got a stop from web {}/{}".format(pr_id, pr_sha1))
                self.jt.stop()
                force_update = False

        # If it wasn't in the queue nor running, then just update the status
        if force_update:
            db_update_job(pr_id, pr_sha1, "Cancelled(F)", "N/A")


    def run(self):
        """Main function taking care of running all jobs in the job queue."""
        while(True):
            time.sleep(3)
            log.debug("Checking for work (queue:{})".format(self.q))

            if len(self.q) > 0:
                with self.lock:
                    pr_id = self.q.pop(0)
                    job = self.job_dict[pr_id]
                log.debug("Handling job: {}".format(pr_id))
                self.jt = JobThread(job)
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

def initialize():
    global initialized

    if not initialized:
        initialize_logger()
        initialize_db()
        initialize_worker_thread()
        log.info("Initialize done!")
        initialized = True

def user_add(pr_id, pr_sha1):
    initialize()
    worker_thread.user_add(pr_id, pr_sha1)

def add(payload):
    initialize()

    if payload is None:
        log.error("Cannot add job without payload")
        return False

    worker_thread.add(payload)
    return True

def cancel(pr_id, pr_sha1):
    initialize()
    if pr_id is None or pr_sha1 is None:
        log.error("Trying to stop a job without a PR number")
    elif worker_thread is None:
        log.error("Threads are not initialized")
    else:
        worker_thread.cancel(pr_id, pr_sha1)

################################################################################
# Debug
################################################################################
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
    initialize()
    add(load_payload_from_file())

if __name__ == "__main__":
    local_run()
    worker_thread.join()
