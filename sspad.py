import cherrypy

from edu.artic.sspad.config import server, app
from edu.artic.sspad.modules import resource, staticImage

class Webapp():
	cherrypy.config.update(server.conf)
	exposed = True

	resource = resource.Resource()
	resource.SI = staticImage.StaticImage()
	#@TODO Add other resource prefixes.
	cherrypy.log('Cherrypy config: ' + str(cherrypy.config))

	def GET(self):
		return {'message': 'Nothing to see here.'}


#print('Name:', __name__)
if __name__ == 'sspad' or __name__ == '__main__':
	cherrypy.tree.mount(Webapp(), '/', app.rest_conf)
	cherrypy.engine.start()
	cherrypy.engine.block()
