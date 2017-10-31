import yaml
import os
import pexpect
import serial
import subprocess
import time

import cfg
import logger

################################################################################
# Relay logic
################################################################################
RELAY_BINARY = "./hidusb-relay-cmd/hidusb-relay-cmd"

class Relay():
    """ Represents an single relay """
    def __init__(self, name, relay_number):
        self.name = name
        self.relay_number = relay_number


    def info(self):
        return "type: %s, number: %d" % (self.name, self.relay_number)


    def turn_on(self):
        if cfg.args is not None and cfg.args.v:
            print("Turning on %s-relay (r: %d)" % (self.name, self.relay_number))
            print("cmd: %s on %d" % (RELAY_BINARY, self.relay_number))
        subprocess.call([RELAY_BINARY, "on", str(self.relay_number)])


    def turn_off(self):
        if cfg.args is not None and cfg.args.v:
            print("Turning off %s-relay (r: %d)" % (self.name, self.relay_number))
            print("cmd: %s off %d" % (RELAY_BINARY, self.relay_number))
        subprocess.call([RELAY_BINARY, "off", str(self.relay_number)])


class PowerRelay(Relay):
    def __init__(self):
        Relay.__init__(self, "power", 1)


    def __str__(self):
        return self.info()


    def power_up(self):
        self.turn_on()


    def power_down(self):
        self.turn_off()


class RecoveryRelay(Relay):
    def __init__(self):
        Relay.__init__(self, "recovery", 2)

    def __str__(self):
        return self.info()


    def enable(self):
        self.turn_on()


    def disable(self):
        self.turn_off()

def cd_check(child, folder):
    """ Helper function to go to a folder and check that we actually entered the
    folder. """
    cmd = "cd %s" % folder
    child.sendline(cmd)
    child.sendline("pwd")
    child.expect(folder, 3)


def do_pexpect(child, cmd=None, exp=None, timeout=5, error_pos=1):
    if cmd is not None:
        print("Sending: %s" % cmd)
        child.sendline(cmd)

    if exp is not None:
        e = []

        # In the yaml file there could be standalone lines or there could be
        # a list if expected output.
        if isinstance(exp, list):
            e = exp + [pexpect.TIMEOUT]
        else:
            e.append(exp)
            e.append(pexpect.TIMEOUT)

        print("Expecting: {} (timeout={}, error={})".format(e, timeout, error_pos))
        r = child.expect(e, timeout)
        print("Got: {} (error at {})".format(r, error_pos))
        if r >= error_pos:
            print("Returning STATUS_FAIL")
            return False

        return True

def spawn_pexpect_child():
    rcfile = os.environ['HOME'] + "/devel/hikey_auto_boot/.bashrc"
    shell = "{} --rcfile {}".format("/bin/bash", rcfile)
    return pexpect.spawn(shell)

def terminate_child(child, git_name, github_nbr):
    child.close()
    logger.store_logfile(git_name, github_nbr, "build.log")


class HiKeyAutoBoard():
    def __init__(self, root=None):
        self.pr = PowerRelay()
        self.rr = RecoveryRelay()
        self.root = root


    def __str__(self):
        return "%s\n%s" % (self.pr, self.rr)


    def power_off(self):
        # They relay is Normally Closed, so we need to turn on the relay to
        # power off the device.
        self.pr.turn_on()


    def power_on(self):
        # They relay is Normally Closed, so we need to turn off the relay to
        # power on the device.
        self.pr.turn_off()


    def power_cycle(self):
        self.power_off()
        time.sleep(0.8)
        self.power_on()


    def enable_recovery_mode(self):
        """ This will power cycle the device and go into recovery mode. """
        self.power_off()
        self.rr.enable()
        time.sleep(1.0)
        self.power_on()


    def disable_recovery_mode(self):
        """ This will turn off the device go back to normal mode. """
        self.power_off()
        self.rr.disable()


    def build(self, yaml_file, clone_url=None, rev=None, git_name=None,
            github_nbr=None):
        """ Function that setup (repo) and build OP-TEE. """
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['build_init_cmds']

        child = spawn_pexpect_child()
        f = open('build.log', 'w')
        child.logfile = f

        print("Initiate build setup ...")
        for i in yml_iter:
            c = i.get('cmd', None)
            e = i.get('exp', None)
            t = i.get('timeout', 5)

            if do_pexpect(child, c, e, t) == False:
                terminate_child(child, git_name, github_nbr)
                return cfg.STATUS_FAIL

        print("Intermediate pre-build step ...")
        folder = "%s/%s" % (cfg.source, git_name)
        cd_check(child, folder)
        
        if clone_url is not None:
            # Add the remote to be able to get the commit to test
            cmd = "git remote add pr_committer %s" % clone_url
            child.sendline(cmd)
            r = child.expect(["", "fatal: remote pr_creator already exists.", pexpect.TIMEOUT])
            if r == 1:
                cmd = "git remote set-url pr_committer" % clone_url
            elif r == 2:
                terminate_child(child, git_name, github_nbr)
                return cfg.STATUS_FAIL

            cmd = "git fetch pr_committer"
            if do_pexpect(child, cmd, None, 60) == False:
                print("Could not fetch from {}".format(clone_url))
                terminate_child(child, git_name, github_nbr)
                return cfg.STATUS_FAIL

            cmd = "git checkout %s" % rev
            exp_string = "HEAD is now at %s" % rev[0:7]
            if do_pexpect(child, cmd, exp_string, 20) == False:
                print("Failed to checkout {}".format(rev))
                terminate_child(child, git_name, github_nbr)
                return cfg.STATUS_FAIL

        print("Starting build ...")
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['build_cmds']

        for i in yml_iter:
            c = i.get('cmd', None)
            e = i.get('exp', None)
            t = i.get('timeout', 5)

            if do_pexpect(child, c, e, t) == False:
                terminate_child(child, git_name, github_nbr)
                return cfg.STATUS_FAIL

        print("Build step complete!")
        terminate_child(child, git_name, github_nbr)
        return cfg.STATUS_OK


    def flash(self, yaml_file):
        """ Function that puts HiKey into recover mode and then flash all boot
        binaries. """
        self.enable_recovery_mode()
        time.sleep(5)

        # Open the yaml file containing all the flash commands etc.
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['flash_cmds']

        child = spawn_pexpect_child()
        f = open('flash.log', 'w')
        child.logfile = f

        print("Flashing the device")

        for i in yml_iter:
            c = i.get('cmd', None)
            e = i.get('exp', None)
            t = i.get('timeout', 5)

            if do_pexpect(child, c, e, t) == False:
                self.disable_recovery_mode()
                return cfg.STATUS_FAIL

        print("Done flashing!")
        self.disable_recovery_mode()
        return cfg.STATUS_OK


    def run_test(self, yaml_file):
        """ Function to run boot up and run xtest. """
        # Open the yaml file containing all the flash commands etc.
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['xtest_cmds']

        child = spawn_pexpect_child()
        f = open('xtest.log', 'w')
        child.logfile = f

        child.sendline("picocom -b 115200 /dev/ttyUSB0")
        child.expect("Terminal ready", timeout=3)

        print("Start running tests")
        self.power_cycle()

        for i in yml_iter:
            c = i.get('cmd', None)
            e = i.get('exp', None)
            t = i.get('timeout', 5)

            if do_pexpect(child, c, e, t) == False:
                self.power_off()
                return cfg.STATUS_FAIL

        print("xtest done!")
        self.power_off()
        return cfg.STATUS_OK
