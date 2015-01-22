import cherrypy

from cherrypy.process.plugins import Daemonizer, PIDFile

from sspad.config import host, server, app
from sspad.controllers import comment_ctrl, static_image_ctrl, tag_cat_ctrl, tag_ctrl, search_ctrl


class Webapp():
    '''Main Web app class.

    Contains the RESTful API and all its top-level locations.
    '''

    exposed = True

    si = static_image_ctrl.StaticImageCtrl()
    tagCat = tag_cat_ctrl.TagCatCtrl()
    tag = tag_ctrl.TagCtrl()
    comment = comment_ctrl.CommentCtrl()
    search = search_ctrl.SearchCtrl()

    def GET(self):
        '''Homepage - does nothing'''

        return {'message': 'Nothing to see here.'}


if __name__ == '__main__':
    cherrypy.config.update(server.conf)

    Daemonizer(cherrypy.engine).subscribe()
    PIDFile(cherrypy.engine, host.pidfile).subscribe()

    webapp = Webapp()
    cherrypy.tree.mount(webapp, '/', app.rest_conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
