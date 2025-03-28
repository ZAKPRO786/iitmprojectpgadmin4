##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2025, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""This is the main application entry point for pgAdmin 4. If running on
a webserver, this will provide the WSGI interface, otherwise, we're going
to start a web server."""

import sys
from flask import Flask, render_template
from flask_socketio import SocketIO
import os
# ✅ Initialize SocketIO
socketio = SocketIO()
TEMPLATE_DIR = os.path.abspath('web/pgadmin/templates')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define the absolute path to the templates folder
TEMPLATE_DIR = os.path.join(BASE_DIR, 'pgadmin', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'pgadmin', 'static')

app = Flask(
    __name__,
    static_url_path='/static',
    static_folder=STATIC_DIR,    # Explicit static path
    template_folder=TEMPLATE_DIR  # Explicit template path
)
if sys.version_info < (3, 8):
    raise RuntimeError('This application must be run under Python 3.8 or later.')

import builtins
import os

# We need to include the root directory in sys.path to ensure that we can
# find everything we need when running in the standalone runtime.
if sys.path[0] != os.path.dirname(os.path.realpath(__file__)):
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

# Grab the SERVER_MODE if it's been set by the runtime
if 'PGADMIN_SERVER_MODE' in os.environ:
    if os.environ['PGADMIN_SERVER_MODE'] == 'OFF':
        builtins.SERVER_MODE = False
    else:
        builtins.SERVER_MODE = True
else:
    builtins.SERVER_MODE = None

import config
import setup
from pgadmin.utils.constants import INTERNAL
from pgadmin.model import SCHEMA_VERSION


##########################################################################
# Support reverse proxying
##########################################################################
class ReverseProxied():
    def __init__(self, app):
        self.app = app
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
            self.app = ProxyFix(app,
                                x_for=config.PROXY_X_FOR_COUNT,
                                x_proto=config.PROXY_X_PROTO_COUNT,
                                x_host=config.PROXY_X_HOST_COUNT,
                                x_port=config.PROXY_X_PORT_COUNT,
                                x_prefix=config.PROXY_X_PREFIX_COUNT)
        except ImportError:
            pass

    def __call__(self, environ, start_response):
        script_name = environ.get("HTTP_X_SCRIPT_NAME", "")
        if script_name:
            environ["SCRIPT_NAME"] = script_name
            path_info = environ["PATH_INFO"]
            if path_info.startswith(script_name):
                environ["PATH_INFO"] = path_info[len(script_name):]
        scheme = environ.get("HTTP_X_SCHEME", "")
        if scheme:
            environ["wsgi.url_scheme"] = scheme
        return self.app(environ, start_response)


##########################################################################
# Sanity checks
##########################################################################
config.SETTINGS_SCHEMA_VERSION = SCHEMA_VERSION

# Check if the database exists. If it does not, create it.
setup_db_required = False
if not os.path.isfile(config.SQLITE_PATH):
    setup_db_required = True

##########################################################################
# Create the app and configure it
##########################################################################

# ✅ Attach SocketIO to the app
socketio.init_app(app)

app.config['sessions'] = dict()

# Load the commit hash
try:
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'commit_hash')) as f:
        config.COMMIT_HASH = f.readline().strip()
except FileNotFoundError:
    config.COMMIT_HASH = None

if setup_db_required:
    setup.setup_db(app)

# Authentication sources
if len(config.AUTHENTICATION_SOURCES) > 0:
    auth_source = [x for x in config.AUTHENTICATION_SOURCES if x != INTERNAL]
    app.PGADMIN_EXTERNAL_AUTH_SOURCE = auth_source[0] if len(auth_source) > 0 else INTERNAL
else:
    app.PGADMIN_EXTERNAL_AUTH_SOURCE = INTERNAL

# Set server properties
app.PGADMIN_RUNTIME = False
app.logger.debug('Config server mode: %s', config.SERVER_MODE)
config.EFFECTIVE_SERVER_PORT = config.DEFAULT_SERVER_PORT

# Handle runtime environment variables
if 'PGADMIN_INT_PORT' in os.environ:
    config.EFFECTIVE_SERVER_PORT = int(os.environ['PGADMIN_INT_PORT'])
if 'PGADMIN_INT_KEY' in os.environ:
    app.PGADMIN_INT_KEY = os.environ['PGADMIN_INT_KEY']
    app.PGADMIN_RUNTIME = True
else:
    app.PGADMIN_INT_KEY = ''

if not app.PGADMIN_RUNTIME:
    app.wsgi_app = ReverseProxied(app.wsgi_app)

##########################################################################
# Routes
##########################################################################
@app.route('/')
def index():
    """Render base.html"""
    return render_template('base.html')


##########################################################################
# Main entry point
##########################################################################
def main():
    """Start the server."""
    try:
        if config.DEBUG:
            socketio.run(
                app,
                host=config.DEFAULT_SERVER,
                port=config.EFFECTIVE_SERVER_PORT,
                debug=config.DEBUG,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        else:
            socketio.run(
                app,
                host=config.DEFAULT_SERVER,
                port=config.EFFECTIVE_SERVER_PORT,
                debug=False,
                allow_unsafe_werkzeug=True
            )
    except KeyboardInterrupt:
        print("Server stopped.")
        socketio.stop()


# Run the server
if __name__ == '__main__':
    main()
