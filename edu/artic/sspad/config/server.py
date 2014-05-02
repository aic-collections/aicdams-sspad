import cherrypy

conf = {
    'global': {
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 5000,
		'log.access_file': '/var/log/sspad/access.log',
		'log.error_file': '/var/log/sspad/error.log',
    },
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
    }
}

