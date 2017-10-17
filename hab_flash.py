#!/usr/bin/env python
# -*- coding: utf-8 -*-

from argparse import ArgumentParser

import pexpect
import serial
import sys
import time
import yaml

gargs = None

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to flash HiKey 620 \
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
        global gargs
        if gargs.v:
            print("Turning on %s-relay (r: %d)" % (self.name, self.relay_number))
            print("cmd: %s on %d" % (RELAY_BINARY, self.relay_number))

    def turn_off(self):
        global gargs
        if gargs.v:
            print("Turning off %s-relay (r: %d)" % (self.name, self.relay_number))
            print("cmd: %s off %d" % (RELAY_BINARY, self.relay_number))


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
        time.sleep(0.5)
        self.power_on()

    def enable_recovery_mode(self):
        """ This will power cycle the device and go into recovery mode. """
        self.power_off()
        self.rr.enable()
        time.sleep(0.5)
        self.power_on()

    def disable_recovery_mode(self):
        """ This will turn off the device go back to normal mode. """
        self.power_off()
        self.rr.disable()

    def flash(self, yaml_file):
        self.enable_recovery_mode()

        # Open the yaml file containing all the flash commands etc.
        with open(yaml_file, 'r') as yml:
            yml_config = yaml.load(yml)
        yml_iter = yml_config['flash_cmds']

        child = pexpect.spawn("/bin/bash")
        f = open('flash.log', 'w')
        child.logfile = f

        print("Flashing the device")

        for i in yml_iter:
            global gargs
            if gargs.v:
                print("cmd: %s, exp: %s (timeout %d)" % (i['cmd'], i['exp'], i['timeout']))
            child.sendline(i['cmd'])
            child.expect(i['exp'], timeout=i['timeout'])

        print("Done flashing!")

        self.disable_recovery_mode()

################################################################################
# Main function
################################################################################
def main(argv):
    print("HiKey auto flasher")

    global gargs
    parser = get_parser()
    gargs = parser.parse_args()

    hab = HiKeyAutoBoard()
    hab.power_cycle()

    flash_config = "hikey_flash_cfg.yaml"
    if gargs.config:
        flash_config = gargs.config

    hab.flash(flash_config)

if __name__ == "__main__":
    main(sys.argv)
