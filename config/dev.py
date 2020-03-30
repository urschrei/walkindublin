# these settings are exported as DEV_CONFIGURATION by fabfile commands
# DEV_CONFIGURATION is then picked up by app/__init__.py

DEBUG = True
reloader = True
# this won't be picked up when running under production
SECRET_KEY = "nope"
