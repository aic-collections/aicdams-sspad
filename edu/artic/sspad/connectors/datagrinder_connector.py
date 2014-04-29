import cherrypy
from http.client import HTTPConnection, HTTPSConnection
from itertools import chain
import mimetypes, urllib, uuid

from edu.artic.sspad.config import host
from edu.artic.sspad.config.datasources import datagrinder_rest_api


class DatagrinderConnector:

	def __init__(self, auth):
		self.auth = auth
		self.conf = datagrinder_rest_api
		self.headers = {'Authorization': self.auth}

	def openSession(self):
		session = \
			HTTPSConnection(self.conf['host'], self.conf['port']) \
			if self.conf['ssl'] \
			else \
			HTTPConnection(self.conf['host'], self.conf['port'])
		if host.app_env != 'prod':
			session.set_debuglevel(1)
		return session


	def resizeImagefromUrl(self, url, w=None, h=None):
		session = self.openSession()
		params = urllib.parse.urlencode({'file': '', 'width': w, 'height': h})
		session.request('GET',\
			self.conf['root'] + 'resize&file={}&width={}&height={}'.format(url, w, h)
		)

		res = session.getresponse()
		return io.BytesIO(res.read())


	def resizeImageFromData(self, image, fname, w=None, h=None):
		session = self.openSession()
		print('Image teaser:', image.peek()[:64])
		#body = urllib.parse.urlencode({'file': image.read(), 'width': w, 'height': h})
		#headers = {"Content-type": "multipart/form-data"}
		fields = [('width', str(w)), ('height', str(h))]
		files = [('file', fname, image.read())]
		body = self.encode_multipart_formdata(fields, files)
		print('Body:', body)
		session.request(
			'POST',
			self.conf['root'] + 'resize',
			body = body
		)

		res = session.getresponse()
		return io.BytesIO(res.read())


	def encode_multipart_formdata(self, fields, files):
		"""
		fields is a sequence of (name, value) elements for regular form fields.
		files is a sequence of (name, filename, value) elements for data to be uploaded as files
		Return (content_type, body) ready for httplib.HTTP instance
		"""
		BOUNDARY = 'BOUNDARY-' + str(uuid.uuid1())
		CRLF = '\r\n'
		L = []
		for (key, value) in fields:
			L.append('--' + BOUNDARY)
			L.append('Content-Disposition: form-data; name="%s"' % key)
			L.append('')
			L.append(value)
		for (key, filename, value) in files:
			L.append('--' + BOUNDARY)
			L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
			L.append('Content-Type: %s' % self.get_content_type(filename))
			L.append('')
			L.append(value)
		L.append('--' + BOUNDARY + '--')
		L.append('')
		print('L:', L)
		body = CRLF.join(L)
		content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
		return content_type, body


	def get_content_type(self, filename):
		return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
