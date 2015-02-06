from abc import ABCMeta

import cherrypy

from cherrypy.lib import cptools

from sspad.modules.content_filter import ContentFilter


class Negotiable(metaclass=ABCMeta):
    '''@package sspad.modules

    Negotiable mixin.
    Provides content negotiation based on Accept request headers.
    '''

    out_fmt = [
        'application/json',
        'application/xml',
        'text/plain',
    ]


    def _output(self, data):
        fmt = cptools.accept(self.out_fmt)
        cherrypy.log('Output format: {}'.format(fmt))
        cherrypy.response.headers['Content-type'] = fmt

        #cherrypy.log('Output: {} '.format(ContentFilter.filter_output(data, fmt)))
        return ContentFilter.filter_output(data, fmt)



