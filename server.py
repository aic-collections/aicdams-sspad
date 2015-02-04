import cherrypy

from cherrypy.process.plugins import Daemonizer, PIDFile

from sspad.config import host, server, app
from sspad.controllers import comment_ctrl, static_image_ctrl, tag_cat_ctrl, tag_ctrl, search_ctrl


class Webapp():
    '''Main Web app class.

    Contains the RESTful API and all its top-level locations.
    '''

    exposed = True


    routes = {
        'si' : static_image_ctrl.StaticImageCtrl,
        'tagCat' : tag_cat_ctrl.TagCatCtrl,
        'tag' : tag_ctrl.TagCtrl,
        'comment' : comment_ctrl.CommentCtrl,
        'search' : search_ctrl.SearchCtrl,
    }



    def OPTIONS(self):
        '''Return list of documented resources.'''

        #cherrypy.log('Dispatch handler: {}'.format(cherrypy.dispatch.RoutesDispatcher.find_handler('/')))
        ret = []
        for r in self.routes:
            ret.append({
                'path' : '/' + r,
                    'info' : self.routes[r].__doc__
            })

        return Webapp.output(ret)



    def GET(self):
        '''Homepage - do nothing'''

        return {'message': 'Nothing to see here.'}



    def output(data):
        if 'prefer' in cherrypy.request.headers:
            cherrypy.log('Prefer headers: {}'.format(cherrypy.request.headers['prefer']))

        return data


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
