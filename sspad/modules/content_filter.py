import json
import dicttoxml

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
            return json.dumps(data).encode('utf8')
        elif mimetype == 'application/xml':
            return dicttoxml.dicttoxml(data)
        else:
            return data.__repr__().encode('utf8')
