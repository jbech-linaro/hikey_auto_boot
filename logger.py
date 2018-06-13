import os
import sqlite3
import pathlib

hab_db_file = "hab.db"
table_job = "jobs"


def store_logfile(git_name, github_nbr, filename):
    if git_name is None or github_nbr is None or filename is None:
        print("Cannot store log file (missing parameters)")
        return

    log_file_dir = "{}/logs/{name}/{nbr}".format(os.getcwd(), name=git_name, nbr=github_nbr)

    try:
        os.stat(log_file_dir)
    except:
        os.makedirs(log_file_dir)

    source = "{d}/{f}".format(d=os.getcwd(), f=filename)
    dest = "{d}/{f}".format(d=log_file_dir, f=filename)

    try:
        os.rename(source, dest)
    except:
        print("Couldn't move log file")

def db_connect():
    return sqlite3.connect('hab.db')

def db_create():
    db = db_connect()
    cursor = db.cursor()
    cursor.execute('''
                    CREATE TABLE jobs(id INTEGER PRIMARY KEY,
                    git_name TEXT,
                    github_nbr TEXT,
                    log_clone TEXT,
                    log_build TEXT,
                    log_flash TEXT,
                    log_run TEXT)
                   ''')
    db.commit()
    db.close()

def db_store_logfile(filename, filetype):
    db_file = pathlib.Path("hab.db")

    if not db_file.exists():
        db_create()

    db = db_connect()
    cursor = db.cursor()

    cursor.execute('''
        INSERT INTO jobs()
        ''')

    db.close()

