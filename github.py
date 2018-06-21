def pr_id(payload):
    """Returns the ID of the GitHub job."""
    return payload['pull_request']['id']


def pr_number(payload):
    """Returns the pull request number."""
    return payload['number']


def pr_sha1(payload):
    """Returns the commit hash (the SHA-1)."""
    return payload['pull_request']['head']['sha']


def pr_clone_url(payload):
    """Returns full URL to the committers own project."""
    return payload['pull_request']['head']['repo']['clone_url']


def pr_name(payload):
    """Returns the name (ex. optee_os) of the Git project."""
    return payload['repository']['name']


def pr_full_name(payload):
    """Returns the full name (ex. OP-TEE/optee_os) of the Git project."""
    return payload['repository']['full_name']
