import cherrypy

from cherrypy.process.plugins import Daemonizer, PIDFile

from sspad.config import host, server, app
from sspad.controllers import comment_ctrl, search_ctrl, sspad_controller, \
        static_image_ctrl, tag_cat_ctrl, tag_ctrl, text_ctrl


class Webapp():
    '''Main Web app class.

    Contains the RESTful API and all its top-level locations.
    '''

    exposed = True

    routes = {
        'comment' : comment_ctrl.CommentCtrl,
        'search' : search_ctrl.SearchCtrl,
        'si' : static_image_ctrl.StaticImageCtrl,
        'tag' : tag_ctrl.TagCtrl,
        'tagCat' : tag_cat_ctrl.TagCatCtrl,
        'tx' : text_ctrl.TextCtrl,
    }



    def OPTIONS(self):
        '''Return list of documented resources.'''

        ret = []
        for r in self.routes:
            ret.append({
                'path' : '/' + r,
                    'info' : self.routes[r].__doc__
            })

        return sspad_controller.SspadController().output(ret)



    def GET(self):
        '''Homepage - do nothing'''

        return sspad_controller.SspadController().output(
                {'message': 'Nothing to see here.'})




if __name__ == '__main__':
    cherrypy.config.update(server.conf)

    Daemonizer(cherrypy.engine).subscribe()
    PIDFile(cherrypy.engine, host.pidfile).subscribe()

    # Set routes as class members as expected by Cherrypy
    for r in Webapp.routes:
        setattr(Webapp, r, Webapp.routes[r]())

    webapp = Webapp()
    cherrypy.tree.mount(webapp, '/', app.rest_conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
