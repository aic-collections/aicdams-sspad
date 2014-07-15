import cherrypy

from cherrypy.process.plugins import Daemonizer, PIDFile

from edu.artic.sspad.config import host, server, app
from edu.artic.sspad.modules import resource, staticImage

class Webapp():
	exposed = True

	resource = resource.Resource()
	resource.SI = staticImage.StaticImage()
	#@TODO Add other resource prefixes.

	def GET(self):
		return {'message': 'Nothing to see here.'}


if __name__ == '__main__':
	cherrypy.config.update(server.conf)

	Daemonizer(cherrypy.engine).subscribe()
	PIDFile(cherrypy.engine, host.pidfile).subscribe()

	webapp = Webapp()
	cherrypy.tree.mount(webapp, '/', app.rest_conf)
	cherrypy.engine.start()
	cherrypy.engine.block()
