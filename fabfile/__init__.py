import os

from fabric.api import env, run, roles, execute, local, cd, hide
from fabric.operations import sudo
from fabric.decorators import task
import virtualenv

env.basename = os.path.dirname(__file__)

# FIXME
env.hosts = ["root@178.128.174.1"]


@task
def deploy():
    """
    Deploy site on remote host
    """
    with cd("/var/www/walkindublin.ie"):
        with hide("output"):
            run("git pull")
            # run("venv/bin/python app.py db upgrade")
            # bust cache
            # execute(bust)
            # soft-restart uWSGI
            sudo("systemctl restart walkindublin")


@task
def reload():
    """ Restart gunicorn and nginx """
    with cd("/var/www/walkindublin.ie"):
        with hide("output"):
            # soft-restart uWSGI
            sudo("systemctl restart walkindublin")
            sudo("systemctl restart nginx")


@task
def bust(db=0):
    """ Bust the remote Redis cache """
    with hide("output"):
        run("redis-cli -n %s flushdb" % db)


@task
def cachesize(db=0):
    """ Show number of entries in remote Redis cache """
    run("redis-cli -n %s dbsize" % db)


@task
def db_init():
    """ Initialise an Alembic migrations environment """
    with cd(env.basename):
        local("venv/bin/python app.py db init")


@task
def db_migrate():
    """ Generate a new migration following changes to Models """
    with cd(env.basename):
        local("venv/bin/python app.py db migrate")


@task
def db_upgrade():
    """ Upgrade DB to HEAD migration """
    with cd(env.basename):
        local("venv/bin/python app.py db upgrade")


@task
def db_downgrade(rev=""):
    """ Downgrade DB to specified revision or base """
    with cd(env.basename):
        local("venv/bin/python app.py db downgrade %s" % rev)


@task
def build():
    """Execute build tasks for all components."""
    virtualenv.build()
    db_init()
    db_migrate()
    db_upgrade()


@task
def run_app():
    """
    Start app in debug mode with reloading turned on. Dev only
    """
    with cd(env.basename):
        # clean up any *.pyc files in our app dir
        local(
            "export DEV_CONFIGURATION=`pwd`/config/dev.py && venv/bin/python ./run.py"
        )


@task
def shell():
    """
    Run iPython without the deprecated Werkzeug stuff
    """
    with cd(env.basename):
        local(
            'export DEV_CONFIGURATION=`pwd`/config/dev.py && venv/bin/ipython -i -c "%run shell.py"'
        )
