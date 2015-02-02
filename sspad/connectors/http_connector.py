import cherrypy
import requests

class HttpConnector:

    def request(self, method, url, **kwargs):
        '''Convenience wrapper that logs each request and raises an exception
        for error codes.

        @param method (string) The HTTP method (case insensitive).
        @param url (string) URL to be requested.
        @param **kwargs Further arguments to be passed to the requests::request() method.

        @return requests.Response
        @throw HTTPError if response code is > 399.
        '''

        cherrypy.log('HttpConnector: {} {}'.format(method.upper(), url))

        ret = requests.request(method.lower(), url, **kwargs)
        cherrypy.log('HttpConnector: return code: {}'.format(ret.status_code))
        ret.raise_for_status()

        return ret
