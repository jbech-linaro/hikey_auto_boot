#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging as log
import yaml

def get_settings_yml_file():
    yml_file = None
    config_file = "configs/settings.yaml"

    try:
        with open(config_file, 'r') as yml:
            yml_file = yaml.load(yml)
    except:
        log.error("Couldn't find {}", config_file)
        exit()

    return yml_file


def config_path():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['config']['path']
    except:
        return "Missing key!"


def repo_bin():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['repo']['bin']
    except:
        return "Missing key!"


def repo_reference():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['repo']['reference']
    except:
        return "Missing key!"


def aarch32_toolchain_path():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['toolchain']['aarch32_path']
    except:
        return "Missing key!"


def aarch64_toolchain_path():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['toolchain']['aarch64_path']
    except:
        return "Missing key!"


def aarch32_prefix():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['toolchain']['aarch32_prefix']
    except:
        return "Missing key!"


def aarch64_prefix():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['toolchain']['aarch64_prefix']
    except:
        return "Missing key!"


def workspace_path():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['workspace']['path']
    except:
        return "Missing key!"


def log_dir():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['log']['dir']
    except:
        return "Missing key!"


def log_file():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['log']['file']
    except:
        return "Missing key!"


def db_file():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['db']['file']
    except:
        return "Missing key!"


def foo():
    yml_file = get_settings_yml_file()
    try:
        return yml_file['foo']['aarch64_path']
    except:
        return "Missing key!"
        

def initialize():
    log.info("Configure settings")
    log.debug("config: {}".format(config_path()))
    log.debug("repo binary: {}".format(repo_bin()))
    log.debug("repo reference: {}".format(repo_reference()))
    log.debug("aarch32_toolchain_path: {}".format(aarch32_toolchain_path()))
    log.debug("aarch64_toolchain_path: {}".format(aarch64_toolchain_path()))
    log.debug("aarch32_prefix: {}".format(aarch32_prefix()))
    log.debug("aarch64_prefix: {}".format(aarch64_prefix()))
    log.debug("workspace_path: {}".format(workspace_path()))
    log.debug("log_dir: {}".format(log_dir()))
    log.debug("log_file: {}".format(log_file()))
    log.debug("db_file {}".format(db_file()))


def initialize_logger():
    LOG_FMT = ("[%(levelname)s] %(funcName)s():%(lineno)d   %(message)s")
    log.basicConfig(
        # filename="core.log",
        level=log.DEBUG,
        format=LOG_FMT,
        filemode='w')


if __name__ == "__main__":
    initialize_logger()
    initialize()
