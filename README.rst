=============================
IBART - I Build And Run Tests
=============================
.. section-numbering::
    :suffix: .

.. contents::

What is IBART?
==============
It's an tool that can initiate a full clone, build, flash, boot and test cycle initiated by a webhook from GitHub. It works with both pure software as well as hardware connected directly to the server. So, a typical use case could be that you have an embedded device that you want to re-flash new software, boot it up and then run some test cases and when done it should report back the status to the GitHub pull request.

How to use IBART
================
- First one needs to setup webhooks_ at GitHub. Important things to configure here is the ``Payload URL``, which should point to the server running IBART. The listening port is by default ``5000``. For ``Content type`` one should select ``application/json``. The secret on the GitHub webhooks page is a string that you need to export in your shell before starting IBART (TODO: add export command). At the section ``Which events would you like to trigger this webhook?`` it is sufficient to select ``Pull requests``.
- Export your GitHub secret before starting IBART:
.. code-block:: bash

    export GITHUB_SECRET="my-github-secret"

- Export your GitHub token  before starting IBART:
.. code-block:: bash

    export GITHUB_TOKEN="my-long-hex-string"

- Set up global settings in ``configs/settings.yaml``
- Write a job definition and store it in ``jobdefs/my-job.yml``
- Run ``./websrv.py``

If everything done correctly, IBART should now be listening for build requests as well as serve HTML queries at http://my-server:5000. 

Configuration
=============
Besides the Python code itself, the following folders are of interest to the one running and configuring IBART.

.. code:: bash

  .
  ├── configs
  ├── database
  ├── jobdefs
  ├── logs
  ├── static
  └── templates


configs
-------
This is the default folder where the main settings for the program is stored.

database
--------
Default folder where there database is stored. It may be wise to use a path pointing outside the IBART root folder to keep the database separated from the git itself. 

jobdefs
-------
Default folder where job definitions are stored. At this moment it can only hold a single job definitition. In the future the idea is to have the ability to add several job definitions here.

logs
----
Default folder where the log files are stored. This is all build logs as well as the debug log from the program itself. It may be wise to use a path pointing outside the IBART root folder to keep the logs separated from the git itself. 

static
------
This is the default Flask static_ folder where things like ``css``, ``javascripts`` etc should be stored.

templates
---------
Default folder for jinja2 ``HTML`` templates.


How jobs are processed
======================
There are two ways to get jobs running. Either it comes as a webhook request from directly from GitHub or it is user request by a user to rebuild a certain job. For GitHub jobs the following happens:

- If it is a new pull reuqest, then a new job will always be added to the queue.
- If it is an update to an existing pull request, then it will first cancel ongoing and remove pending jobs and then add the updated pull request to the queue. I.e., there can only be a single job in the queue for a given pull request when it is a build request coming from GitHub.

If it is an user initiated request, then following applies:

- TODO

Job definitions - Yaml-files
============================

Exported variables
------------------
Under the hood IBART uses pexpect_ and for each section the job-definition file (yaml) it will spawn a new shell. This means that things are not normally carried over between sections in the job-definition file. But since it is both cumbersome and easy to forget export the same things over and over again, IBART saves every export it sees and when entering a new section it will export the same environment variables again. So, from a user perspective exports will work as expected.

Directory changes
-----------------
Just as for the exported variables the last seen ``cd`` command is saved and then executed when spawning a new shell on for a new section in the job definition file. I.e., from user perspective a ``cd`` will carry over to the section in the job definition file.

Security considerations
=======================
This is a very early version and there are things are not secure:

- There has been no real attempt yet to protect against SQL injection.
- Anyone can restart and stop a job by going to the main page on IBART.
- It runs Flask ``debug`` mode by default.
- Whatever is in the job definition file will be executed and it will do this with the same permissions as the server itself. So if one type ``cmd: rm -rf $HOME`` in the job definition file, then all files in the servers' $HOME folder **will** be deleted. So be very careful with what you or someone else puts into job definition file. 

.. _pexpect: http://pexpect.readthedocs.io/en/stable/index.html
.. _static: http://flask.pocoo.org/docs/1.0/quickstart/#static-files
.. _webhooks: https://developer.github.com/webhooks/creating
