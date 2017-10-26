import threading
import time

# Local import
from dbg import pr
import cfg
import gitcmd
import hab_builder
import hab_flash
import hab_xtest

# The jobs consist of a dictionary that contains the actual jobs and the
# job_queue (a list) it self is a simple queue where we only keep the id's to
# know what order to work through the posted jobs.
jobs = {}
job_queue = []

main_thread = None

class Job():
    def __init__(self, nbr, url=None, hash_commit=None, name=None):
        self.id = nbr
        self.name = name
        self.url = url
        self.hash = hash_commit
        self.repo_init = None
        self.ok = True
        self.running = False
        self.done = False

    def __str__(self):
        s = "id:        %s\n" % self.id
        s += "name:      %s\n" % self.name
        s += "URL:       %s\n" % self.url
        s += "hash:      %s\n" % self.hash
        s += "repo init: %s" % self.repo_init
        return s

    def add_repo_init_cmd(self, cmd):
        self.repo_init = cmd


def get_running_time(time_start):
    m, s = divmod(time.time() - time_start, 60)
    h, m = divmod(m, 60)
    return "%sh %sm %ss" % (h, m, round(s, 2))


def run_job():
    global job_queue
    pr("Start listening for jobs!\n")
    while True:
        time.sleep(3)
        if job_queue:
            time_start = time.time()
            j = job_queue.pop(0)
            jobs[j].running = True
            url = jobs[j].url
            revision = jobs[j].hash
            name = jobs[j].name

            if hab_builder.build(None, url, revision, name) is not cfg.STATUS_OK:
                # TODO: The error message should go all the way back to GitHub
                pr("Failed building job")
                jobs[j].ok = False

            if jobs[j].ok and hab_flash.flash() is not cfg.STATUS_OK:
                # TODO: The error message should go all the way back to GitHub
                pr("Failed flashing the device")
                jobs[j].ok = False

            if jobs[j].ok and hab_xtest.test() is not cfg.STATUS_OK:
                # TODO: The error message should go all the way back to GitHub
                pr("Failed running test")

            jobs[j].done = True
            jobs[j].running = False
            print("Job completed (%s : %s)" % (j, get_running_time(time_start)))


def initialize_main_thread():
    global main_thread
    # Return if thread is already running.
    if main_thread != None:
        return

    main_thread = threading.Thread(target=run_job)
    main_thread.setDaemon(True)
    main_thread.start()

def add_job(jpl):
    global job_queue

    # 1. Grab necessary information
    nbr = jpl['number']
    name = gitcmd.project_name(jpl)
    url = gitcmd.url(jpl)
    hash_commit = gitcmd.hash_commit(jpl)

    # 2. Create a job
    job_desc = "%s-%d" % (name, nbr)
    j = Job(job_desc, name, url, hash_commit)
    print(j)

    # 3. Initialize the thread picking up new jobs
    initialize_main_thread()

    # 4. Check if there already is a job
    if j.id in job_queue:
        pr("Job already exist")
        pr(job_queue)
        # TODO: Stop current job if running
        # TODO: Remove job from the current location and put it last in the list
        # TODO: Don't just add another job
        job_queue.append(j.id)
    else:
        pr("New job!")
        jobs[j.id] = j
        job_queue.append(j.id)


