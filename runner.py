import os
import requests
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
    def __init__(self,
            json_blob=None,
            git_name="test",
            github_nbr="9999",
            clone_url=None,
            ref=None):

        self.json_blob = json_blob
        self.git_name = git_name
        self.github_nbr = github_nbr
        self.clone_url = clone_url
        self.ref = ref

        self.ok = True
        self.running = False
        self.done = False

    def __str__(self):
        s = "name:      %s\n" % self.git_name
        s += "github_nbr %s\n" % self.github_nbr
        s += "clone_url: %s\n" % self.clone_url
        s += "ref:       %s\n" % self.ref
        return s

    def get_build_id(self):
        """ The build id is the key for the Job dictionary and is a combination
        of the name of the git and the pull request number. """
        return "{}-{}".format(self.git_name, "-", self.github_nbr)



def get_running_time(time_start):
    m, s = divmod(time.time() - time_start, 60)
    h, m = divmod(m, 60)
    return "%sh %sm %ss" % (h, m, round(s, 2))


def update_state(state, statuses_url, git_name, github_number, description):
    request = { "context": "OP-TEE HiKey auto builder" }
    request['state'] = state
    request['target_url'] = "http://jyx.mooo.com/{}/{}".format(git_name, github_number)
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
            update_state("pending", statuses_url, j.git_name, j.github_nbr,
                         "Job added to the queue")

            # Building ...
            if hab_builder.build(None, j.clone_url, j.ref, j.git_name) \
                    is not cfg.STATUS_OK:
                print("Failed building job")
                update_state("error", statuses_url, j.git_name, j.github_nbr,
                             "Failed building the solution")
                j.ok = False

            # Flashing ...
            if j.ok and hab_flash.flash() is not cfg.STATUS_OK:
                print("Failed flashing the device")
                update_state("error", statuses_url, j.git_name, j.github_nbr,
                             "Failed flashing the device(s)")
                j.ok = False

            # Running xtest ...
            if j.ok and hab_xtest.test() is not cfg.STATUS_OK:
                update_state("error", statuses_url, j.git_name, j.github_nbr,
                             "xtest ended with errors")
                print("Failed running test")

            j.done = True
            j.running = False

            if j.ok:
                update_state("success", statuses_url, j.git_name, j.github_nbr,
                             "Everything OK")
            print("Job ended (%s : %s)" % (bi, get_running_time(time_start)))


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
    git_name = gitcmd.project_name(jpl)
    github_nbr = gitcmd.number(jpl)
    clone_url = gitcmd.clone_url(jpl)
    ref = gitcmd.ref(jpl)

    # 2. Create a job
    j = Job(jpl, git_name, github_nbr, clone_url, ref)
    print(j)

    # 3. Initialize the thread picking up new jobs
    initialize_main_thread()

    # 4. Check if there already is a job
    update_state("pending", gitcmd.statuses_url(jpl), git_name, github_nbr,
            "Job added to the queue")

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
