import cherrypy
rest_conf = {
    '/': {
        'tools.json_out.on': True,
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'request.methods_with_bodies': ('POST', 'PUT', 'PATCH'),
    },
}

