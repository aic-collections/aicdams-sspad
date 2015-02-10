from sspad.controllers.sspad_controller import SspadController
from sspad.models.annotation import Annotation

import requests


class AnnotationCtrl(SspadController):
    '''Annotation Controller class.

    Handles operations with annotations.

    @package sspad.controllers
    @author Stefano Cossu <scossu@artic.edu>
    @date 12/11/2014
    '''


    exposed = True


    @property
    def model(self):
        '''@sa SspadController::model'''

        return Annotation



    def GET(self, subject):
        '''Lists all annotations for the given subject URI.

        @param uri (string) Subject URI.

        @return (list) List of annotation dicts.
        '''

        return self._output(self.model().list(subject))



    def POST(self, subject, content):
        '''Create an Annotation.

        @param subject (string) URI of subject Resource.
        @param content (string) Content of the annotation.

        @return (dict) Message with new Annotation node information.
        '''

        return self._output(self.model().create(subject, content))



