from dbg import pr

import gitcmd

jobs = {}

class Job():
    def __init__(self, nbr, url=None, hash_commit=None):
        self.id = nbr
        self.url = url
        self.hash = hash_commit
        self.repo_init = None

    def __str__(self):
        s = "id:        %s\n" % self.id
        s += "URL:       %s\n" % self.url
        s += "hash:      %s\n" % self.hash
        s += "repo init: %s" % self.repo_init
        return s

    def add_repo_init_cmd(self, cmd):
        self.repo_init = cmd


def add_job(jpl):
    # 1. Grab necessary information
    nbr = jpl['number']
    name = gitcmd.project_name(jpl)
    url = gitcmd.url(jpl)
    hash_commit = gitcmd.hash_commit(jpl)

    # 2. Create a job
    job_desc = "%s-%d" % (name, nbr)
    j = Job(job_desc, url, hash_commit)
    print(j)

    # 3. Check if there already is a job
    if j.id in jobs:
        pr("Job already exist")
    else:
        pr("New job!")
        jobs[j.id] = j


