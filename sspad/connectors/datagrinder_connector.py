import cherrypy, io, requests
from cherrypy import log
#from requests_toolbelt import MultipartEncoder

from sspad.config.datasources import datagrinder_rest_api


class DatagrinderConnector:
    '''Datagrinder connector class.

    Handles requests to datagrinder for multimedia processing.
    '''

    @property
    def _conf(self):
        '''Datagrinder host configuration.

        @return dict
        '''

        return datagrinder_rest_api



    @property
    def _base_url(self):
        '''Base URL built from conf parameters.

        @return string
        '''

        return '{}://{}{}'. format(self._conf['proto'], self._conf['host'], self._conf['root'])



    ## METHODS ##

    def __init__(self):
        '''Class constructor.

        Sets authorization parameters based on incoming auth headers.

        @return None
        '''

        auth_str = cherrypy.request.headers['Authorization']\
            if 'Authorization' in cherrypy.request.headers\
            else None
        self.headers = {'Authorization': auth_str}



    def resizeImagefromUrl(self, url, w=None, h=None):
        '''Resizes an image downloaded from a URL reference.

        @param url (string) Source image URL.
        @param w (int) Maximum width in pixels.
        @param h (int) Maximum height in pixels.

        @return (BytesIO) The resized image stream.
        '''

        params = {'file': url, 'width': w, 'height': h}
        res = requests.get(
            self._base_url + 'resize.jpg',
            params = params
        )

        cherrypy.log('Image resize response:', res.status_code)
        res.raise_for_status()
        return io.BufferedReader(res.content)



    def resizeImageFromData(self, image, fname, w=0, h=0):
        '''Resizes an image downloaded from a provided datastream.

        @param image (BytesIO) Image datastream.
        @param w (int) Maximum width in pixels.
        @param h (int) Maximum height in pixels.

        @return BytesIO The resized image stream.
        '''

        data = {'width': w, 'height': h}
        files = {'file': (fname, image)}

        res = requests.post(
            self._base_url + 'resize.jpg',
            files = files,
            data = data
        )

        cherrypy.log('Image resize response: ' + str(res.status_code))
        res.raise_for_status()
        #print('Returned image:', res.content[:256])
        return io.BytesIO(res.content)


