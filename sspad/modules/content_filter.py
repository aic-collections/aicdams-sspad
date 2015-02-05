import cherrypy
import json
import dicttoxml

from xml.dom.minidom import parseString

class ContentFilter():
    '''@package sspad.modules

    ContentFilter class.
    This class serializes native Python data structures to various formats
    according to given mime types.
    '''

    def filter_output(data, mimetype):
        '''Filter output based on mimetype.

        @param data A python dict or other iterable object.
        @param mimetype (string) MIME type of the output format.

        @return string
        '''

        if mimetype == 'application/json':
            return json.dumps(data, indent=4).encode('utf8')
        elif mimetype == 'application/xml':
            #dicttoxml.set_debug(filename=cherrypy.config['log.error_file'])
            ret = dicttoxml.dicttoxml(data, custom_root='response')
            dom = parseString(ret)
            return dom.toprettyxml().encode('utf8')
        else:
            return data.__repr__().encode('utf8')
