import cherrypy

from sspad.config.host import host

if host['app_env'] == 'prod':
    logdir = '/var/log/sspad/'
elif host['app_env'] == 'stag':
    logdir = '/var/log/sspad-staging/'
elif host['app_env'] == 'test':
    logdir = '/var/log/sspad-test/'
else:
    logdir = '/var/log/sspad-dev/'

## CherryPy server configuration.
conf = {
    'global': {
        'log.access_file': logdir + 'access.log',
        'log.error_file': logdir + 'error.log',
        'server.max_request_body_size': host['max_req_size'],
        'server.socket_host': host['listen_addr'],
        'server.socket_port': host['listen_port'],
    }
}

