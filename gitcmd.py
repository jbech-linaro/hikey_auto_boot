from dbg import pr

GITHUB = "https://github.com"

def hash_commit(jpl):
    """ Returns the commit hash (the SHA-1). """
    return jpl['pull_request']['head']['sha']

def checkout_cmd(jpl):
    """ Returns command to be used the force checking out a particular commit. """
    return "git reset --hard " + hash_commit(jpl)

def url(jpl):
    """ Returns full URL to the committers own project. """
    return GITHUB + "/" + jpl['pull_request']['head']['repo']['full_name']

def remote_string(jpl):
    """ Returns command to be used when adding a remote. """
    return "git remote add commiter " + url(jpl)

def branch(jpl):
    """ Returns the name of the commiters branch. """
    return jpl['pull_request']['head']['ref']

def project_name(jpl):
    """ Returns the name of the Git project. """
    return jpl['repository']['name']
