import cherrypy
import re

from abc import ABCMeta

from sspad.models.sspad_model import SspadModel
from sspad.modules.negotiable import Negotiable


class SspadController(Negotiable, metaclass=ABCMeta):
    ''' Main SSPAD controller.

    @package sspad.controllers
    '''

    @property
    def model(self):
        '''Returns the model class associated with this controller.

        Calling self.model() in a HTTP exposed method sets up connections
        with external datasources providing credentials passed in the HTTP
        headers.
        Therefore, it is good practice to instantiate the model for each call
        and, if this is used multiple times in the same HTTP
        exposed method, use a variable to refer to the same model instance.

        @return Class
        '''

        return SspadModel



    def OPTIONS(self):
        '''OPTIONS method.

        Display HTTP methods, model properties and types(mixins) available.

        @return string JSON-encoded dict.
        '''

        exp_methods = [m for m in dir(self) \
                if callable(getattr(self, m)) \
                and re.match('^[A-Z]+$', m)]

        #cherrypy.log('HTTP methods: {}'.format(exp_methods))
        method_doc = []
        for method in exp_methods:
            method_doc.append(getattr(self, method).__doc__)
        #cherrypy.log('Method docs: {}'.format(method_doc))

        docs = {
            'methods' : method_doc,
            'props' : [{'prop' : i[0], 'type' : i[1], 'data_type' : str(i[2]) \
                    if len(i)>2 else None} for i in self.model().ns_props],
        }
        if hasattr(self.model, 'mixins'):
            docs['types'] = self.model().mixins

        return self._output(docs)
