# -*- coding: utf-8 -*-
import glob
import json
import logging as log
import os
import pexpect
import re
import sys
import threading
import time
import yaml
import zipfile

from collections import OrderedDict
from pathlib import Path

# Local modules
import db
import github
import job
import settings
import status
import utils

###############################################################################
# Pexpect
###############################################################################


last_cd = None
export_history = []


def get_yaml_cmd(yml_iter):
    cmd = yml_iter.get('cmd', None)
    exp = yml_iter.get('exp', None)
    check_ret = yml_iter.get('chkret', "y")
    to = yml_iter.get('timeout', 3)

    # Force check_ret to None if there is exp.
    if exp is not None:
        check_ret = None
    log.debug("cmd: {}, exp: {}, chkret: {}, timeout: {}".format(
        cmd, exp, check_ret, to))
    return cmd, exp, check_ret, to


def do_pexpect(child, cmd=None, exp=None, check_retval=None, timeout=5,
               error_pos=1):
    if exp is not None and check_retval is not None:
        log.error("Cannot expect both a string and return value at the time!")
        return False

    if cmd is not None:
        log.debug("Sending: {}".format(cmd))
        # Save the last cd command for other build stages
        if cmd.startswith("cd "):
            global last_cd
            last_cd = cmd

        if cmd.startswith("export "):
            global export_history
            export_history.append(cmd)

        # Append echo $? to the command in case the user specified that the
        # return value from a command should be checked
        if check_retval is not None:
            child.sendline("{};echo $?".format(cmd))
        else:
            child.sendline(cmd)

    # Start with a clean expect list
    e = []
    if exp is not None:
        # In the yaml file there could be standalone lines or there could be
        # a list if expected output.
        if isinstance(exp, list):
            e = exp + [pexpect.TIMEOUT]
        else:
            e.append(exp)
            e.append(pexpect.TIMEOUT)
    elif check_retval is not None:
        # A good return value contains a single '0' followed by IBART on next
        # line.
        e.append('\r\n0\r\nIBART')
        e.append(pexpect.TIMEOUT)

        # A bad line is any number not starting with '0' followed by IBART on
        # the next line.
        e.append(r'\r\n[^0]\d*\r\nIBART')

    if exp is not None or check_retval is not None:
        log.debug("Expecting (exp): {} (timeout={}, error={})".format(
            e, timeout, error_pos))
        r = child.expect(e, timeout)
        log.debug("Got: {} (value >= {} is considered an error)".format(
            r, error_pos))
        if r >= error_pos:
            return False

    return True


def export_variables(child, job):
    """This function exports any information that could be used by the one
    writing the yaml scripts for a particular job. Typically one want to export
    the information coming from GitHub here."""
    exported_variables = [
            "export PR_SHA1={}".format(job.pr_sha1()),
            "export PR_NUMBER={}".format(job.pr_number()),
            "export PR_NAME={}".format(job.pr_name()),
            "export PR_FULL_NAME={}".format(job.pr_full_name()),
            "export PR_CLONE_URL={}".format(job.pr_clone_url()),
            "export PR_BRANCH={}".format(job.pr_branch())
    ]

    for e in exported_variables:
        child.sendline(e)
        child.expect('')


def spawn_pexpect_child(job):
    global last_cd
    global export_history

    if job is None:
        log.error("Trying to spawn child with no Job")
        return

    rcfile = '--rcfile {}/.bashrc'.format(os.getcwd())
    child = pexpect.spawnu('/bin/bash', ['--rcfile', rcfile],
                           encoding='utf-8')

    # Make environment variables available in YAML job definitions.
    export_variables(child, job)

    # Export previous exports to the new shell
    if export_history:
        for e in export_history:
            child.sendline(e)

    # Go to last known 'cd' directory.
    # NOTE!!! This must be here after doing the exports, otherwise things like
    # $ cd $SOME_VARIABLE will probably fail.
    if last_cd is not None:
        child.sendline(last_cd)

    child.sendline('export PS1="IBART $ "')
    r = child.expect(['IBART \$ ', pexpect.TIMEOUT], 2)
    if r > 0:
        log.error("Could not set PS1\n{}".format(child.before))
        return None

    return child


def terminate_child(child):
    child.close()

###############################################################################
# SQLITE3
###############################################################################


LOG_PRE_CLONE = 0
LOG_CLONE = 1
LOG_POST_CLONE = 2
LOG_PRE_BUILD = 3
LOG_BUILD = 4
LOG_POST_BUILD = 5
LOG_PRE_FLASH = 6
LOG_FLASH = 7
LOG_POST_FLASH = 8
LOG_PRE_BOOT = 9
LOG_BOOT = 10
LOG_POST_BOOT = 11
LOG_PRE_TEST = 12
LOG_TEST = 13
LOG_POST_TEST = 14

d_logstr = {
        LOG_PRE_CLONE: "pre_clone",
        LOG_CLONE: "clone",
        LOG_POST_CLONE: "post_clone",

        LOG_PRE_BUILD: "pre_build",
        LOG_BUILD: "build",
        LOG_POST_BUILD: "post_build",

        LOG_PRE_FLASH: "pre_flash",
        LOG_FLASH: "flash",
        LOG_POST_FLASH: "post_flash",

        LOG_PRE_BOOT: "pre_boot",
        LOG_BOOT: "boot",
        LOG_POST_BOOT: "post_boot",

        LOG_PRE_TEST: "pre_test",
        LOG_TEST: "test",
        LOG_POST_TEST: "post_test"
        }

# -----------------------------------------------------------------------------
# Log handling
# -----------------------------------------------------------------------------


def get_logs(pr_full_name, pr_number, pr_id, pr_sha1):
    """The function returns a dictionary with dictionaries where the high level
       dictionary have 'key' corresponding job definition and the inner
       dictionaries corresponds to each individual log files."""
    if (pr_full_name is None or pr_number is None or pr_id is None or
            pr_sha1 is None):
        log.error("Cannot store log file (missing parameters)")
        return

    log_file_dir = "{p}/{fn}/{n}/{i}/{s}".format(
            p=settings.log_dir(), fn=pr_full_name, n=pr_number, i=pr_id,
            s=pr_sha1)

    log.debug("Getting logs from folder: {}".format(log_file_dir))

    all_logs = OrderedDict()
    for zf in sorted(glob.glob("{}/*.zip".format(log_file_dir))):
        logs = OrderedDict()
        log.debug("Unpacking zip-file: {}".format(zf))
        for key, logtype in d_logstr.items():
            filename = "{}.log".format(logtype)
            logs[logtype] = read_log(filename, zf)
        # Use job definition as key when return log from multi definition
        # jobs.
        jd = Path(zf).name.replace(".zip", "")
        all_logs[jd] = logs
    return all_logs


def read_log(filename, zip_file):
    """This function extracts a single log file from a certain zip-file."""
    if filename is None or zip_file is None:
        log.error("Cannot read log file (missing parameters)")
        return

    log_line = ""
    try:
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        # TODO: Get rid of "logs/"
        filename = "logs/{}".format(filename)
        with zipfile.ZipFile(zip_file) as myzip:
            with myzip.open(filename) as myfile:
                log_line = ansi_escape.sub('', myfile.read().decode('utf-8'))
    except (IOError, KeyError) as e:
        pass

    # Add line numbers to the log
    ctr = 1
    numbered_log = []
    for l in log_line.split('\n'):
        numbered_log.append("{:>6}:  {}".format(ctr, l))
        ctr += 1

    # If there is no content in the log, then don't return anything
    if len(numbered_log) == 1 and len(numbered_log[0]) == 9:
        return None

    return "\n".join(numbered_log)


def clear_logfiles(payload):
    if payload is None:
        log.error("Cannot clear log file (missing parameters)")
        return

    pr_full_name = github.pr_full_name(payload)
    pr_number = github.pr_number(payload)
    pr_id = github.pr_id(payload)
    pr_sha1 = github.pr_sha1(payload)

    log_file_dir = "{p}/{fn}/{n}/{i}/{s}".format(
            p=settings.log_dir(), fn=pr_full_name, n=pr_number, i=pr_id,
            s=pr_sha1)

    for zf in glob.glob("{}/*.zip".format(log_file_dir)):
        if os.path.isfile(zf):
            os.remove(zf)


def store_logfile(payload, current_file, full_log_file):
    if (payload is None or current_file is None or full_log_file is None):
        log.error("Cannot store log file (missing parameters)")
        return

    pr_full_name = github.pr_full_name(payload)
    pr_number = github.pr_number(payload)
    pr_id = github.pr_id(payload)
    pr_sha1 = github.pr_sha1(payload)

    log_file_dir = "{p}/{fn}/{n}/{i}/{s}".format(
            p=settings.log_dir(), fn=pr_full_name, n=pr_number, i=pr_id,
            s=pr_sha1)

    try:
        os.stat(log_file_dir)
    except FileNotFoundError:
        os.makedirs(log_file_dir)

    source = current_file
    dest = "{d}/{f}".format(d=log_file_dir, f=full_log_file)

    try:
        zipfile.ZipFile(dest, mode='a',
                        compression=zipfile.ZIP_DEFLATED).write(source)
    except FileNotFoundError:
        log.error("Couldn't find file {}".format(dest))



def get_job_definitions():
    return sorted([jd for jd in glob.glob("jobdefs/*.yaml")])



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

    def start_job(self):
        global d_logstr

        jobdefs = get_job_definitions()

        # Just local to save some typing further down
        payload = self.job.payload

        # To prevent old logs from showing up on the web-page, start by
        # removing all of them.
        clear_logfiles(payload)

        for jd in jobdefs:
            log.info("Start clone, build ... sequence for {}".format(self.job))

            # Replace .yaml with .zip
            full_log_file = Path(jd).name.replace(".yaml", ".zip")

            log.debug("full_log_file: {}".format(full_log_file))

            with open(jd, 'r') as yml:
                yml_config = yaml.load(yml)

            # Loop all defined values
            for k, logtype in d_logstr.items():
                try:
                    yml_iter = yml_config[logtype]
                except KeyError:
                    continue

                child = spawn_pexpect_child(self.job)
                current_log_file = "{}/{}.log".format(settings.log_dir(),
                                                      logtype)
                with open(current_log_file, 'w') as f:
                    child.logfile_read = f

                    if yml_iter is None:
                        store_logfile(payload, current_log_file, full_log_file)
                        continue

                    for i in yml_iter:
                        log.debug("")
                        c, e, cr, to = get_yaml_cmd(i)

                        if not do_pexpect(child, c, e, cr, to):
                            terminate_child(child)
                            log.error("job type: {} failed!".format(logtype))
                            store_logfile(payload, current_log_file,
                                          full_log_file)
                            github.update_state(payload, "failure", "Stage {} "
                                                "failed!".format(logtype))
                            return status.FAIL

                        if self.stopped():
                            terminate_child(child)
                            log.debug("job type: {} cancelled!".format(
                                      logtype))
                            store_logfile(payload, current_log_file,
                                          full_log_file)
                            github.update_state(payload, "failure", "Job was "
                                                "stopped by user (stage {})!"
                                                "".format(logtype))
                            return status.CANCEL

                    terminate_child(child)
                store_logfile(payload, current_log_file, full_log_file)

        github.update_state(payload, "success", "All good!")
        return status.SUCCESS

    def run(self):
        """This is the main function for running a complete clone, build, flash
        and test job."""
        global export_history
        current_status = status.d[status.RUNNING]

        log.debug("Job/{} : {}".format(current_status, self.job))
        time_start = time.time()

        pr_id = self.job.pr_id()
        pr_sha1 = self.job.pr_sha1()

        db.update_job(pr_id, pr_sha1, current_status, "N/A")
        github.update_state(self.job.payload, "pending", "Job running!")

        current_status = status.d[self.start_job()]

        export_history.clear()

        running_time = utils.get_running_time(time_start)
        log.debug("Job/{} : {} --> {}".format(current_status, self.job,
                  running_time))
        db.update_job(pr_id, pr_sha1, current_status, running_time)

###############################################################################
# Worker
###############################################################################


worker_thread = None


class WorkerThread(threading.Thread):
    """Thread class responsible to adding and running jobs."""
    def __init__(self, group=None, target=None, name=None, args=(),
                 kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.q = []
        self.job_dict = {}
        self.jt = None
        self.lock = threading.Lock()

    def user_add(self, pr_id, pr_sha1):
        if pr_id is None or pr_sha1 is None:
            log.error("Missing pr_id or pr_sha1 when trying to submit user "
                      "job")
            return

        with self.lock:
            log.info("Got user initiated add {}/{}".format(pr_id, pr_sha1))
            payload = db.get_payload_from_pr_id(pr_id, pr_sha1)
            if payload is None:
                log.error("Didn't find payload for ID:{}".format(pr_id))
                return

            pr_id_sha1 = "{}-{}".format(pr_id, pr_sha1)
            self.q.append(pr_id_sha1)
            self.job_dict[pr_id_sha1] = job.Job(payload, True)
            db.update_job(pr_id, pr_sha1, status.d[status.PENDING], "N/A")
            github.update_state(payload, "pending", "Job added to queue")

    def add(self, payload):
        """Responsible of adding new jobs the the job queue."""
        if payload is None:
            log.error("Missing payload when trying to add job")
            return

        pr_id = github.pr_id(payload)
        pr_number = github.pr_number(payload)
        pr_sha1 = github.pr_sha1(payload)
        pr_full_name = github.pr_full_name(payload)

        with self.lock:
            log.info("Got GitHub initiated add {}/{} --> PR#{}".format(
                     pr_id, pr_sha1, pr_number))
            # Check whether the jobs in the current queue touches the same PR
            # number as this incoming request does.
            for i, elem in enumerate(self.q):
                job_in_queue = self.job_dict[elem]
                # Remove existing jobs as long as they are not user initiated
                # jobs.
                if (job_in_queue.pr_number() == pr_number and
                        job_in_queue.pr_full_name() == pr_full_name):
                    if not job_in_queue.user_initiated:
                        log.debug("Non user initiated job found in queue, "
                                  "removing {}".format(elem))
                        del self.q[i]
                        db.update_job(job_in_queue.pr_id(),
                                      job_in_queue.pr_sha1(),
                                      status.d[status.CANCEL], "N/A")
                        github.update_state(job_in_queue.payload,
                                            "failure", "Job cancelled!")

            # Check whether current job also should be stopped (i.e, same
            # PR, but _not_ user initiated).
            if (self.jt is not None and
                    self.jt.job.pr_number() == pr_number and
                    self.jt.job.pr_full_name == pr_full_name and not
                    self.jt.job.user_initiated):
                log.debug("Non user initiated job found running, "
                          "stopping {}".format(self.jt.job))
                self.jt.stop()

            pr_id_sha1 = "{}-{}".format(pr_id, pr_sha1)
            self.q.append(pr_id_sha1)
            new_job = Job(payload, False)
            self.job_dict[pr_id_sha1] = new_job
            db.add_build_record(new_job.payload)
            db.update_job(pr_id, pr_sha1, status.d[status.PENDING], "N/A")
            github.update_state(payload, "pending", "Job added to queue")

    def cancel(self, pr_id, pr_sha1):
        force_update = True

        # Stop pending jobs
        for i, elem in enumerate(self.q):
            job_in_queue = self.job_dict[elem]
            if (job_in_queue.pr_id() == pr_id and
                    job_in_queue.pr_sha1() == pr_sha1):
                log.debug("Got a stop from web {}/{}".format(pr_id, pr_sha1))
                del self.q[i]
                db.update_job(job_in_queue.pr_id(), job_in_queue.pr_sha1(),
                              status.d[status.CANCEL], "N/A")
                force_update = False

        # Stop the running job
        if self.jt is not None:
            if (self.jt.job.pr_id() == pr_id and
                    self.jt.job.pr_sha1() == pr_sha1):
                log.debug("Got a stop from web {}/{}".format(pr_id, pr_sha1))
                self.jt.stop()
                force_update = False

        # If it wasn't in the queue nor running, then just update the status
        if force_update:
            db.update_job(pr_id, pr_sha1, status.d[status.CANCEL], "N/A")
            payload = db.get_payload_from_pr_id(pr_id, pr_sha1)
            github.update_state(payload, "failure", "Job cancelled!")

    def run(self):
        """Main function taking care of running all jobs in the job queue."""
        while(True):
            time.sleep(3)

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
    if worker_thread is not None:
        return

    worker_thread = WorkerThread()
    worker_thread.setDaemon(True)
    worker_thread.start()
    log.info("Worker thread has been started")

###############################################################################
# Logger
###############################################################################


def initialize_logger():
    LOG_FMT = ("[%(levelname)s] %(funcName)s():%(lineno)d   %(message)s")
    log.basicConfig(
        filename=settings.log_file(),
        level=log.DEBUG,
        format=LOG_FMT)


###############################################################################
# Main
###############################################################################
initialized = False


def initialize():
    global initialized

    if not initialized:
        initialize_logger()
        db.initialize()
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

