#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging as l
import os
import requests
import threading
import time
import random
from collections import deque

# Local import
from dbg import pr
import cfg
import hab_builder
import hab_flash
import hab_xtest
import log_type
import core_logger

class Job():
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
        l.info("Stopping PR {}".format(self.job.pr))
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        if self.stopped():
            return
        l.info("Job {} running!".format(self.job))
        time.sleep(3)
        if self.stopped():
            l.info("Job {} has been requsted to stop the work!".format(self.job))
            return
        time.sleep(3)
        if self.stopped():
            l.info("Job {} has been requsted to stop the work!".format(self.job))
            return
        time.sleep(3)
        if self.stopped():
            l.info("Job {} has been requsted to stop the work!".format(self.job))
            return
        time.sleep(3)
        l.info("Done with Job {}!".format(self.job))

worker_thread = None

class WorkerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
            args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target,
                name=name)
        self.args = args
        self.kwargs = kwargs
        self.q = deque()
        self.jt = None
        return

    def add(self, pr):
        # Remove pending jobs affecting same PR from the queue
        while self.q.count(pr) > 0:
            l.debug("PR{} pending, removing it from queue".format(pr))
            self.q.remove(pr)

        # If the ongoing work is from the same PR, then stop that too
        if self.jt is not None:
            if self.jt.job.pr == pr:
                l.info("The new/updated PR ({}) have a corresponding job running, sending stop()".format(pr))
                self.jt.stop()

        # Finally add the new/updated PR to the queue
        self.q.append(pr)
        l.info("Added PR{}".format(pr))

    def run(self):
        while(True):
            time.sleep(1)
            l.info("Checking for work (q:{})".format(self.q))

            if len(self.q) > 0:
                pr = self.q.popleft()
                l.info("Handling job: {}".format(pr))
                self.jt = JobThread(Job(pr))
                self.jt.start()
                self.jt.join()
                self.jt = None
        return

def initialize_worker_thread():
    global worker_thread
    # Return if thread is already running.
    if worker_thread != None:
        return

    worker_thread = WorkerThread()
    worker_thread.setDaemon(True)
    worker_thread.start()
    l.info("Worker thread has been started")

def test():
    LOG_FMT = "[%(levelname)s] %(filename)-16s%(funcName)s():%(lineno)d # %(message)s"
    l.basicConfig(#filename=cfg.core_log,
        level = l.DEBUG,
        format = LOG_FMT,
        filemode = 'w')
    l.info("Runnint test")

    initialize_worker_thread()

    for j in range(0, 5):
        worker_thread.add(5)

    while (True):
        pr = random.randint(1, 10)
        worker_thread.add(pr)
        time.sleep(random.randint(1, 2))


    # Wait forever
    worker_thread.join()
    l.info("Bailing out")

if __name__ == "__main__":
    test()
