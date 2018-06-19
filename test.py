#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
import threading
import pexpect
import sys

my_global_data = None

def change_me():
    global my_global_data
    my_global_data = 1111
    return

def ret_many():
    return 1, 2, 3

class A():

    def __init__(self, data=None):
        self.data = data
        self.my_global_data = data

    def __str__(self):
        return "data:{}\nmy_global_data:{}".format(self.data, self.my_global_data)

    def change(self):
        global my_global_data
        change_me()
        print("my_global_data:{}".format(my_global_data))

class FileAdapter(object):
    def __init__(self, logger=None):
        self.logger = logger
        self.foo = 123

    def write(self, data):
        # NOTE: data can be a partial line, multiple lines
        data = data.strip() # ignore leading/trailing whitespace
        print("----->  {}".format(data))

    def flush(self):
        print("---- LET ME FLUSH ----")
        pass  # leave it to logging to flush properly

def main():
    print("Start")
    a = A(123)
    print(a)
    a.change()

    my_cmd = "sleep 1"
    my_exp = "logd.db"
    c = pexpect.spawnu(my_cmd)
    c.logfile = FileAdapter()
    print("Expect ...")
    dir(c.expect)
    r = c.expect([my_exp, pexpect.EOF, pexpect.TIMEOUT], timeout=3)
    print(r)
    #log = c.before
    #print(c.after)

    #print("I sent: {}".format(my_cmd))
    #print("I got:\n{}".format(log))
    a, b, c = ret_many()
    print("{}, {}, {}".format(a, b, c))

if __name__ == "__main__":
    main()
