import imp
import os
import sys


sys.path.insert(0, os.path.dirname(__file__))

os.environ['FLASK_ADMIN_PASSWORD'] = os.getenv('FLASK_ADMIN_PASSWORD', '1326')
wsgi = imp.load_source('wsgi', 'app.py')
application = wsgi.app
