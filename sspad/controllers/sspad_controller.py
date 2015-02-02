import cherrypy

from abc import ABCMeta

from sspad.models.sspad_model import SspadModel


class SspadController(metaclass=ABCMeta):
    ''' Main SSPAD controller.

    @package sspad.controllers
    '''

    @property
    def model(self):
        '''Returns the model class associated with this controller.

        Calling self.model() in a HTTP exposed method sets up connections with external
            datasources providing credentials passed in the HTTP headers. Therefore, it is good practice
            to instantiate the model for each call and, if this is used multiple times in the same HTTP
            exposed method, use a variable to refer to the same model instance.

        @return Class
        '''

        return SspadModel



    def OPTIONS(self):
        '''OPTIONS method.

        Display HTTP methods, model properties and types(mixins) available.

        @return string JSON-encoded dict.
        '''

        return {
            'avaiable_methods' : [
                # @TODO use introspection & docstring methods
            ],
            'available_props' : self.model().props,
            'available_types' : self.model().mixins,
        }




