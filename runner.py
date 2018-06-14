import logging as l
import os
import requests
import threading
import time
from collections import deque

# Local import
from dbg import pr
import cfg
import gitcmd
import hab_builder
import hab_flash
import hab_xtest
import log_type
import core_logger



class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = threading.Event()
        self.q = deque()
        self.current = None
        self.job_thread = JobThread()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def add_job(self, pr_id, pr_number, git_name):
        l.info("Adding {pi}:{gn}/{pn}".format(pi=pr_id,
            gn=git_name, pn=pr_number))
        self.q.append(j)
            

    def get_job(self):
        self.current = self.q.popleft()
        return self.current

    def get_current(self):
        return self.current

    def remove_all_jobs(self):
        self.q.clear()

    def run(self):
        while True:
            time.sleep(3)
            if self.stopped():
                return
            try:
                job = self.get_job()
                print("Handling job: {}".format(job))
            except IndexError:
                pass

# The jobs consist of a dictionary that contains the actual jobs and the
# job_queue (a list) it self is a simple queue where we only keep the id's to
# know what order to work through the posted jobs.
jobs = {}
job_queue = []

main_thread = None

class Job():
    def __init__(self,
            json_blob=None,
            pr_id=9999,
            git_name="test",
            github_nbr="9999",
            clone_url=None,
            ref=None):

        self.json_blob = json_blob
        self.pr_id = pr_id
        self.git_name = git_name
        self.github_nbr = github_nbr
        self.clone_url = clone_url
        self.ref = ref

        self.ok = True
        self.running = False
        self.done = False

        self.clone_log = None
        self.build_log = None
        self.flash_log = None
        self.run_log = None

    def __str__(self):
        s = "Job::"
        s += "  pr_id:     %s\n" % self.pr_id
        s += "  name:      %s\n" % self.git_name
        s += "  github_nbr %s\n" % self.github_nbr
        s += "  clone_url: %s\n" % self.clone_url
        s += "  ref:       %s\n" % self.ref
        return s

    def get_build_id(self):
        """ The build id is the key for the Job dictionary and is a combination
        of the name of the git and the pull request number. """
        return "{}-{}".format(self.git_name, "-", self.github_nbr)

    def add_log(log, logtype):
        if logtype == log_type.CLONE:
            self.clone_log = log
        elif logtype == log_type.BUILD:
            self.build_log = log
        elif logtype == log_type.FLASH:
            self.flash_log = log
        elif logtype == log_type.RUN:
            self.run_log = log
        else:
            print("Trying to add unknown log type!")

    def get_log(logtype):
        if logtype == CLONE:
            return self.clone_log
        elif logtype == log_type.BUILD:
            return self.build_log
        elif logtype == log_type.FLASH:
            return self.flash_log
        elif logtype == log_type.RUN:
            return self.run_log
        else:
            print("Trying to get an unknown log type!")
            return None


def get_running_time(time_start):
    m, s = divmod(time.time() - time_start, 60)
    h, m = divmod(m, 60)
    return "%sh %sm %ss" % (h, m, round(s, 2))


def update_state(state, statuses_url, git_name, github_number, description):
    request = { "context": "OP-TEE HiKey auto builder" }
    request['state'] = state
    request['target_url'] = "{}/{}/{}".format(cfg.target_url, git_name, github_number)
    request['description'] = description

    print(request)

    # Read the personal token (from GitHub)
    token = "token {}".format(os.environ['GITHUB_TOKEN'])

    # Set the token
    headers = {'content-type': 'application/json',
            'Authorization': token }

    # Note that this will print sensitive information
    # print(headers)

    res = requests.post(statuses_url, json=request, headers=headers)
    # print("response from server: {}".format(res.text))


def run_job():
    global job_queue
    print("Start listening for jobs!\n")
    while True:
        time.sleep(3)
        if job_queue:
            time_start = time.time()

            # Get the build id so we can find it in the dictionary with Jobs
            bi = job_queue.pop(0)

            j = jobs[bi]
            j.running = True

            statuses_url = j.json_blob['pull_request']['statuses_url']
            kpdate_state("pending", statuses_url, j.git_name, j.github_nbr,
                         "Job added to the queue")

            # Building ...
            if hab_builder.build(None, j.clone_url, j.ref, j.git_name,
                    j.github_nbr) is not cfg.STATUS_OK:
                print("Failed building job")
                update_state("error", statuses_url, j.git_name, j.github_nbr,
                             "Failed building the solution")
                j.ok = False

            # Flashing ...
            if j.ok and hab_flash.flash(None, j.clone_url, j.ref, j.git_name,
                    j.github_nbr) is not cfg.STATUS_OK:
                print("Failed flashing the device")
                update_state("error", statuses_url, j.git_name, j.github_nbr,
                             "Failed flashing the device(s)")
                j.ok = False

            # Running xtest ...
            if j.ok and hab_xtest.test(None, j.clone_url, j.ref, j.git_name,
                    j.github_nbr) is not cfg.STATUS_OK:
                print("Failed running test")
                update_state("error", statuses_url, j.git_name, j.github_nbr,
                             "xtest ended with errors")
                j.ok = False

            j.done = True
            j.running = False

            if j.ok:
                update_state("success", statuses_url, j.git_name, j.github_nbr,
                             "Everything OK")
            print("Job ended (%s : %s)" % (bi, get_running_time(time_start)))


def initialize_job_thread():
    global main_thread
    # Return if thread is already running.
    if main_thread != None:
        return

    LOG_FMT = "%(levelname)s:%(asctime)s %(funcName)s:%(lineno)d # %(message)s"
    l.basicConfig(filename=cfg.core_log,
        level = l.DEBUG,
        format = LOG_FMT,
        filemode = 'w')

    main_thread = StoppableThread()
    main_thread.setDaemon(True)
    main_thread.start()
    l.info("Started job thread")


def add_job(jpl):
    global job_queue

    # 1. Grab necessary information (according to the main.html page)
    pr_id = gitcmd.pull_request_id(jpl)
    git_name = gitcmd.project_name(jpl)
    github_nbr = gitcmd.pull_request_number(jpl)
    clone_url = gitcmd.clone_url(jpl)
    ref = gitcmd.ref(jpl)

    # 2. Create a job
    j = Job(jpl, pr_id, git_name, github_nbr, clone_url, ref)
    print(j)

    # 3. Initialize the thread picking up new jobs
    initialize_job_thread()

    # 4. Let the GitHub pull request know that the job has been added
    update_state("pending", gitcmd.statuses_url(jpl), git_name, github_nbr,
            "Job added to the queue")

    # 5. Check if there already is a job
    build_id = j.get_build_id()
    if build_id in job_queue:
        print("Job ({}) already exist".format(build_id))
        print(job_queue)
        # TODO: Stop current job if running
        # TODO: Remove job from the current location and put it last in the list
        # TODO: Don't just add another job
        job_queue.append(build_id)
    else:
        print("New job!")
        # Put the new job in the dictionary with Jobs
        jobs[build_id] = j

        # Append the build id to the queue
        job_queue.append(build_id)

job_id = 1
def test_job_start():
    global job_id
    initialize_job_thread()

    l.info("Got a new job")
    pr_id = 183720495
    pr_number = 2274
    git_name = "OP-TEE/optee_os"

    main_thread.add_job(pr_id, pr_number, git_name)
    job_id += 1

def test_job_stop():
    global main_thread
    l.info("Stopping all jobs")
    main_thread.stop()
    main_thread.join()
    main_thread = None
