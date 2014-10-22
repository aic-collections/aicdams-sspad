import cherrypy

from cherrypy.process.plugins import Daemonizer, PIDFile

from sspad.config import host, server, app
from sspad.modules import list, staticImage


## Main Web app class.
#
# Contains the RESTful API and all its top-level locations.
class Webapp():
	exposed = True

	list = list.List()
	asset.si = staticImage.StaticImage()
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
