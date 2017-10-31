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
def build(argv=None, clone_url=None, rev=None, git_name=None, github_nbr=None):
    print("HiKey auto builder")

    if (argv is not None):
        parser = get_parser()
        cfg.args = parser.parse_args()

    h = hab.HiKeyAutoBoard()

    build_config = "hikey_job_cfg.yaml"
    if cfg.args is not None and cfg.args.config:
        build_config = cfg.args.config

    print("Building {cu} {rev} {gn} {gnbr}".format(cu=clone_url, rev=rev, gn=git_name,
        gnbr=github_nbr))
    return h.build(build_config, clone_url, rev, git_name, github_nbr)


if __name__ == "__main__":
    build(sys.argv)
