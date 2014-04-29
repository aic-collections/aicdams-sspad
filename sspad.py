import cherrypy

from edu.artic.sspad.config import host, server
from edu.artic.sspad.modules import resource, staticImage

class Webapp():
	_cp_config = {
		'tools.json_out.on': True,
	#	'tools.json_in.on': True
	}
	exposed = True

	resource = resource.Resource()
	resource.SI = staticImage.StaticImage()
	#@TODO Add other resource prefixes.

	def GET(self):
		return {'message': 'Nothing to see here.'}


if __name__ == '__main__':
	cherrypy.quickstart(Webapp(), config=server.conf)
