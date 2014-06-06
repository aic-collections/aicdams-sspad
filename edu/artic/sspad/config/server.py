import cherrypy

conf = {
    'global': {
		'log.access_file': '/var/log/sspad/access.log',
		'log.error_file': '/var/log/sspad/error.log',
		'server.max_request_body_size': 256 * 1024 * 1024, # 256Mb
		'server.socket_host': '0.0.0.0',
		'server.socket_port': 5000,
    },
    '/': {
		'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
		#'request.methods_with_bodies': ('POST', 'PUT', 'PATCH'),
    }
}

