import yaml
import pexpect
import serial
import subprocess
import time

import cfg

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


    def build(self, yaml_file, url=None, revision=None, git_name=None):
        """ Function that setup (repo) and build OP-TEE. """
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['build_init_cmds']

        child = pexpect.spawn("/bin/bash")
        f = open('build.log', 'w')
        child.logfile = f

        print("Initiate build setup ...")
        for i in yml_iter:
            if cfg.args is not None and cfg.args.v:
                print("cmd: %s, exp: %s (timeout %d)" % (i['cmd'], i['exp'], i['timeout']))
            child.sendline(i['cmd'])
            child.expect(i['exp'], timeout=i['timeout'])


        print("Intermedia pre-build step ...")
        folder = "%s/%s" % (cfg.source, git_name)
        cd_check(child, folder)
        
        cmd = "git remote add pr_committer %s" % url
        child.sendline(cmd)
        r = child.expect(["", "fatal: remote pr_creator already exists."])
        if r == 1:
            cmd = "git remote set-url pr_committer" % url

        cmd = "git fetch pr_committer"
        child.sendline(cmd)
        child.expect("", 60)

        cmd = "git checkout %s" % revision
        child.sendline(cmd)
        exp_string = "HEAD is now at %s" % revision[0:7]
        child.expect(exp_string, 10)


        print("Starting build ...")
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['build_cmds']

        for i in yml_iter:
            if cfg.args is not None and cfg.args.v:
                print("cmd: %s, exp: %s (timeout %d)" % (i['cmd'], i['exp'], i['timeout']))
            child.sendline(i['cmd'])
            e = [pexpect.TIMEOUT]

            # In the yaml file there could be standalone lines of there could be
            # a list if expected output.
            if isinstance(i['exp'], list):
                e = e + i['exp']
            else:
                e.append(i['exp'])
            print(e)
            # We subtract by one since we have added the timeout in the expected
            # array.
            retval = child.expect(e, timeout=i['timeout']) - 1
            print("Retval %d" % retval)
            try:
                if retval >= i['error_pos']:
                    print("Returning STATUS_FAIL")
                    return cfg.STATUS_FAIL
            except KeyError:
                # error_pos not existing ...
                pass

        print("Build step complete!")
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

        child = pexpect.spawn("/bin/bash")
        f = open('flash.log', 'w')
        child.logfile = f

        print("Flashing the device")

        for i in yml_iter:
            if cfg.args is not None and cfg.args.v:
                print("cmd: %s, exp: %s (timeout %d)" % (i['cmd'], i['exp'], i['timeout']))
            child.sendline(i['cmd'])
            child.expect(i['exp'], timeout=i['timeout'])

        print("Done flashing!")

        self.disable_recovery_mode()
        return cfg.STATUS_OK


    def run_test(self, yaml_file):
        """ Function to run boot up and run xtest. """
        # Open the yaml file containing all the flash commands etc.
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['xtest_cmds']

        child = pexpect.spawn("/bin/bash")
        f = open('xtest.log', 'w')
        child.logfile = f

        child.sendline("picocom -b 115200 /dev/ttyUSB0")
        child.expect("Terminal ready", timeout=3)

        print("Start running tests")
        self.power_cycle()

        for i in yml_iter:
            if cfg.args is not None and cfg.args.v:
                print("cmd: %s, exp: %s (timeout %d)" % (i['cmd'], i['exp'], i['timeout']))
            if i['cmd'] is not None:
                child.sendline(i['cmd'])
            child.expect(i['exp'], timeout=i['timeout'])

        print("xtest done!")
        self.power_off()
        return cfg.STATUS_OK
