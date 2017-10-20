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

def build(job):
    pr("--> Building job: %s:" % job.id)
    time_start = time.time()
    time.sleep(random.randint(3, 15))
    pr("<-- Done (%s : %s)" % (job.id, get_running_time(time_start)))

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
def main(argv):
    print("HiKey auto builder")

    parser = get_parser()
    cfg.args = parser.parse_args()

    h = hab.HiKeyAutoBoard()

    build_config = "hikey_flash_cfg.yaml"
    if cfg.args.config:
        build_config = cfg.args.config

    h.build(build_config)

if __name__ == "__main__":
    main(sys.argv)
