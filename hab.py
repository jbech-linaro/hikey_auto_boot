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


    def build(self, yaml_file, url=None, revision=None, name=None):
        """ Function that setup (repo) and build OP-TEE. """
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['build_cmds']

        child = pexpect.spawn("/bin/bash")
        f = open('build.log', 'w')
        child.logfile = f

        print("Building ...")

        for i in yml_iter:
            if cfg.args is not None and cfg.args.v:
                print("cmd: %s, exp: %s (timeout %d)" % (i['cmd'], i['exp'], i['timeout']))
            # TODO: Fix this when _not_ using a shell script for building, this
            # is an ugly hardcoded hack.
            print("cmd %s" % i['cmd'])
            if i['cmd'] == "./init_repo_and_build.sh":
                cmd = "%s %s %s %s" % (i['cmd'], url, revision, name)
                print("New cmd: %s" % cmd)
                child.sendline(cmd)
            else:
                child.sendline(i['cmd'])
            child.expect(i['exp'], timeout=i['timeout'])

        print("Done building!")
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
