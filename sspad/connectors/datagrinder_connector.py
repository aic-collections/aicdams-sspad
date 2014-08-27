import cherrypy, io, requests
from cherrypy import log
#from requests_toolbelt import MultipartEncoder

from sspad.config.datasources import datagrinder_rest_api


## Datagrinder connector class.
#
#  Handles requests to datagrinder for multimedia processing.
class DatagrinderConnector:

	## Datagrinder host configuration.
	_conf = datagrinder_rest_api

	## Base URL built from conf parameters.
	_base_url = '{}://{}{}'. format(_conf['proto'], _conf['host'], _conf['root'])


	## Class constructor.
	#
	# Sets authorization parameters based on incoming auth headers.
	#
	#  @param string auth Authorization string as passed by incoming headers.
	def __init__(self, auth):
		self.auth = auth
		self.headers = {'Authorization': self.auth}


	## Resizes an image downloaded from a URL reference.
	#
	#  @param url (string) Source image URL.
	#  @param w (int) Maximum width in pixels.
	#  @param h (int) Maximum height in pixels.
	#
	#  @return BytesIO The resized image stream.
	def resizeImagefromUrl(self, url, w=None, h=None):
		params = {'file': url, 'width': w, 'height': h}
		res = requests.get(
			self._base_url + 'resize.jpg',
			params = params
		)

		cherrypy.log('Image resize response:', res.status_code)
		res.raise_for_status()
		return io.BufferedReader(res.content)


	## Resizes an image downloaded from a provided datastream.
	#
	#  @param image (BytesIO) Image datastream.
	#  @param w (int) Maximum width in pixels.
	#  @param h (int) Maximum height in pixels.
	#
	#  @return BytesIO The resized image stream.
	def resizeImageFromData(self, image, fname, w=0, h=0):
		data = {'width': w, 'height': h}
		files = {'file': (fname, image)}

		res = requests.post(
			self._base_url + 'resize.jpg',
			files = files,
			data = data
		)

		cherrypy.log('Image resize response: ' + str(res.status_code))
		#cherrypy.log('Image resize headers: ' + str(res.headers))
		res.raise_for_status()
		#print('Returned image:', res.content[:256])
		cherrypy.log('After image resize: {}'.format(image.closed))
		return io.BytesIO(res.content)


