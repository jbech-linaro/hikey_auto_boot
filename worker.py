#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging as l
import threading
import time
import random
from collections import deque

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
        l.info("Stopping PR {}".format(self.job.pr))
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        """This is the main function for running a complete clone, build, flash
        and test job."""
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
    """Thread class responsible to adding and running jobs."""
    def __init__(self, group=None, target=None, name=None,
            args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.q = deque()
        self.jt = None
        return

    def add(self, pr):
        """Responsible of adding new jobs the the job queue."""
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
        """Main function taking care of running all jobs in the job queue."""
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
    """Initialize the main thread responsible for adding and running jobs."""
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
