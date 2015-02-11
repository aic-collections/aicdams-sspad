import cherrypy

from sspad.controllers.annotation_ctrl import AnnotationCtrl
from sspad.models.comment import Comment


class CommentCtrl(AnnotationCtrl):
    '''Comment Controller class.

    Handles operations with comments.

    @package sspad.controllers
    @author Stefano Cossu <scossu@artic.edu>
    @date 12/11/2014
    '''


    exposed = True


    @property
    def model(self):
        '''@sa SspadController::model'''

        return Comment



    def GET(self, subject, cat=None):
        '''GET method.

        Lists all annotations for the given subject URI.

        @param uri (string) Subject URI.

        @return (list) List of annotation dicts.
        '''

        return self._output(self.model().list(subject, cat))



    def POST(self, subject, content, cat=None):
        '''POST method.

        Create an Annotation.

        @param subject (string) URI of subject Resource.
        @param content (string) Content of the Comment.
        @param category (string) Comment category.

        @return (dict) Message with new Annotation node information.
        '''

        cherrypy.log('\n')
        cherrypy.log('*****************')
        cherrypy.log('Creating comment.')
        cherrypy.log('*****************')
        cherrypy.log('')

        return self._output(
                self.model().create(subject, content, cat))

