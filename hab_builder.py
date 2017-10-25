#!/usr/bin/env python
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
import random
import sys
import time

# Local imports
from dbg import pr
import cfg
import hab

def get_running_time(time_start):
    m, s = divmod(time.time() - time_start, 60)
    h, m = divmod(m, 60)
    return "%sh %sm %ss" % (h, m, round(s, 2))

def old_build(job):
    pr("--> Building job: %s:" % job.id)
    time_start = time.time()
    time.sleep(random.randint(3, 15))
    pr("<-- Done (%s : %s)" % (job.id, get_running_time(time_start)))
    # TODO: Figure out how to catch timeout/errors from pyexpect
    return cfg.STATUS_OK

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to build HiKey 620 \
            automatically')

    parser.add_argument('-v', required=False, action="store_true", \
            default=False, \
            help='Output some verbose debugging info')

    parser.add_argument('--project', required=False, action="store_true", \
            default=False, \
            help='Full path to the repo project making the HiKey build')

    parser.add_argument('-c', '--config', required=False, action="store", \
            default=None, \
            help='Use a yaml flash config file')

    return parser

################################################################################
# Main function
################################################################################
def build(argv=None, url=None, revision=None, name=None):
    print("HiKey auto builder")

    if (argv is not None):
        parser = get_parser()
        cfg.args = parser.parse_args()

    h = hab.HiKeyAutoBoard()

    build_config = "hikey_job_cfg.yaml"
    if cfg.args is not None and cfg.args.config:
        build_config = cfg.args.config

    # TODO: Just for testing debugging
    url = "https://github.com/jbech-linaro/optee_os"
    git_name = "optee_os"
    rev = "aef1df91cbe6e14840bada3dfb72efe204ae495c"
    print("Building %s %s %s" % (url, rev, git_name))
    return h.build(build_config, url, rev, git_name)


if __name__ == "__main__":
    build(sys.argv)
