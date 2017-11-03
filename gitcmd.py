from dbg import pr

GITHUB = "https://github.com"

def ref(jpl):
    """ Returns the commit hash (the SHA-1). """
    return jpl['pull_request']['head']['sha']

def checkout_cmd(jpl):
    """ Returns command to be used the force checking out a particular commit. """
    return "git reset --hard " + hash_commit(jpl)

def clone_url(jpl):
    """ Returns full URL to the committers own project. """
    return jpl['pull_request']['head']['repo']['clone_url']

def remote_string(jpl):
    """ Returns command to be used when adding a remote. """
    return "git remote add commiter " + clone_url(jpl)

def branch(jpl):
    """ Returns the name of the commiters branch. """
    return jpl['pull_request']['head']['ref']

def project_name(jpl):
    """ Returns the name of the Git project. """
    return jpl['repository']['name']

def statuses_url(jpl):
    """ Returns the name of the status URL to the Git project. """
    return jpl['pull_request']['statuses_url']

def number(jpl):
    """ Returns the name of the status URL to the Git project. """
    return jpl['number']
