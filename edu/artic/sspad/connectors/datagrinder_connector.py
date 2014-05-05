import cherrypy, io, requests
from cherrypy import log
#from requests_toolbelt import MultipartEncoder

from edu.artic.sspad.config.datasources import datagrinder_rest_api


class DatagrinderConnector:

	conf = datagrinder_rest_api
	base_url = '{}://{}{}'. format(conf['proto'], conf['host'], conf['root'])


	def __init__(self, auth):
		self.auth = auth
		self.headers = {'Authorization': self.auth}


	def resizeImagefromUrl(self, url, w=None, h=None):
		params = {'file': url, 'width': w, 'height': h}
		res = requests.get(
			self.base_url + 'resize.jpg',
			params = params
		)

		print('Image resize response:', res.status_code)
		res.raise_for_status()
		return io.BufferedReader(res.content)


	def resizeImageFromData(self, image, fname, w=0, h=0):
		fields = {'width': w, 'height': h}
		files = {'file': (fname, image)}
		'''
		m = MultipartEncoder(fields = {
			'width': bytes([w]), 'height': bytes([h]),
			'file': (fname, image)
		})
		print('Payload: ', m.to_string())
		'''

		res = requests.post(
			self.base_url + 'resize.jpg',
			data = fields,
			files = files
			#data=m
		)

		log.error('Image resize response: ' + str(res.status_code))
		res.raise_for_status()
		#print('Returned image:', res.content[:256])
		return io.BytesIO(res.content)


