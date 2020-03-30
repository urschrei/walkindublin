import os
from fabric.context_managers import settings, hide
from fabric.colors import cyan
from utils import do
from __init__ import upgrade_db


config_file_path = "migrations/alembic.ini"


def build():
    """Initialise and migrate database to latest version."""
    print(cyan("\nUpdating database..."))
    with settings(hide("warnings"), warn_only=True):
        if not os.path.exists(config_file_path):
            do("alembic -c %s init db/postgresql" % config_file_path)
        upgrade_db()
