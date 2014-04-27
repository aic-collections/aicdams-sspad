import bottle
from http.client import HTTPConnection, HTTPSConnection
from itertools import chain
import urllib.parse

from edu.artic.sspad.config import host
from edu.artic.sspad.config.datasources import datagrinder_rest_api


class DatagrinderConnector:

	def __init__(self):
		self.conf = datagrinder_rest_api
		self.auth = bottle.request.headers.get('Authorization')
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


	def resizeImagefromUrl(url, w=None, h=None):
		self.openSession()
		params = urllib.parse.urlencode({'file': '', 'width': w, 'height': h})
		self.session.request('GET',\
			self.conf['root'] + 'resize&file={}&width={}&height={}'.format(url, w, h)
		)


	def resizeImagefromData(image, w=None, h=None):
		self.openSession()
		params = urllib.parse.urlencode({'file': '', 'width': w, 'height': h})
		self.session.request('POST', self.conf['root'] + 'resize')
