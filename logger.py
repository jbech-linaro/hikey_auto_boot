import os

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
