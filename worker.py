#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging as log
import json
import threading
import time
import random
from collections import deque

class Singleton(type):
    instance = None
    def __call__(cls, *args, **kw):
        if not cls.instance:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance

################################################################################
# GitHub Json
################################################################################
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
    def __init__(self, pr=None):
        self.pr = pr

    def __str__(self):
        return "{}".format(self.pr)

class JobThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
regularly for the stopped() condition."""

    def __init__(self, job):
        super(JobThread, self).__init__()
        self._stop_event = threading.Event()
        self.job = job

    def stop(self):
        log.debug("Stopping PR {}".format(self.job.pr))
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        """This is the main function for running a complete clone, build, flash
        and test job."""
        if self.stopped():
            return
        log.debug("START Job : {}".format(self.job))
        time.sleep(3)
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
        self.jt = None
        return

    def add(self, pr, payload=None):
        """Responsible of adding new jobs the the job queue."""
        # Remove pending jobs affecting same PR from the queue
        while self.q.count(pr) > 0:
            log.debug("PR{} pending, removing it from queue".format(pr))
            self.q.remove(pr)

        # If the ongoing work is from the same PR, then stop that too
        if self.jt is not None:
            if self.jt.job.pr == pr:
                log.debug("The new/updated PR ({}) have a corresponding job running, sending stop()".format(pr))
                self.jt.stop()

        # Finally add the new/updated PR to the queue
        self.q.append(pr)
        log.info("Added PR{}".format(pr))

    def run(self):
        """Main function taking care of running all jobs in the job queue."""
        while(True):
            time.sleep(1)
            log.debug("Checking for work (q:{})".format(self.q))

            if len(self.q) > 0:
                pr = self.q.popleft()
                log.debug("Handling job: {}".format(pr))
                self.jt = JobThread(Job(pr))
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
    if not initialized:
        initialize_logger()
        initialize_worker_thread()
        initialize_github(payload)
        log.info("Initialize done!")

def debug_test():
    for j in range(0, 5):
        worker_thread.add(5)

    while (True):
        pr = random.randint(1, 10)
        worker_thread.add(pr)
        time.sleep(random.randint(1, 2))

def add(payload=None):
    initialize(payload)

    # This is basically just for testing
    if payload is None:
        debug_test()
    else:
        global gh
        pr = gh.pr_number()
        worker_thread.add(pr, payload)

def local_run():
    payload = None
    with open('last_blob.json', 'r') as f:
        payload = f.read()
    add(json.loads(payload))
    time.sleep(1)
    add(json.loads(payload))
    time.sleep(1)
    add(json.loads(payload))
    time.sleep(1)
    add(json.loads(payload))

if __name__ == "__main__":
    local_run()
    worker_thread.join()
