import random
import time

# Local imports
from dbg import pr

def get_running_time(time_start):
    m, s = divmod(time.time() - time_start, 60)
    h, m = divmod(m, 60)
    return "%sh %sm %ss" % (h, m, round(s, 2))

def build(job):
    pr("--> Building job: %s:" % job.id)
    time_start = time.time()
    time.sleep(random.randint(3, 15))
    pr("<-- Done (%s : %s)" % (job.id, get_running_time(time_start)))
