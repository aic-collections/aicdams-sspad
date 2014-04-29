import cherrypy

conf = {
    'global': {
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 5000,
    },
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
    }
}

