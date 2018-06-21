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
    d = {1: "a", 2: "b", 3: "c"}
    for k, v in d.items():
        print(v)

    cmd = "cd /tmp/"
    if cmd.startswith("cd "):
        print("y")
    else:
        print("n")



if __name__ == "__main__":
    main()
