import abc, mimetypes, re
import cherrypy

from edu.artic.sspad.connectors.datagrinder_connector import DatagrinderConnector
from edu.artic.sspad.connectors.fedora_connector import FedoraConnector
from edu.artic.sspad.connectors.tstore_connector import TstoreConnector
from edu.artic.sspad.connectors.uidminter_connector import UidminterConnector

class Resource():
	''' Top-level class that handles resources. '''

	#exposed = True
	add_mimetypes = [
		('image/jpeg', '.jpeg', True),
		('image/psd', '.psd', False),
		('image/vnd.adobe.photoshop', '.psd', True),
		('image/x-psd', '.psd', False),
		# [...]
	]

	def __init__(self):
		self._setConnection()

		mimetypes.init()
		for mt, ext, strict in self.add_mimetypes:
			mimetypes.add_type(mt, ext, strict)


	def _setConnection(self):
		'''Set connectors.'''
		
		print('Setting up connections.')
		self.auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.fconn = FedoraConnector(self.auth_str)
		self.dgconn = DatagrinderConnector(self.auth_str)
		self.tsconn = TstoreConnector(self.auth_str)


	def mintUid(self, mid=None):
		try:
			uid = UidminterConnector().mintUid(self.pfx, mid)
		except:
			raise RuntimeError('Could not generate UID.')
		return uid


	def openTransaction(self):
		return self.fconn.openTransaction()


	def createNodeInTx(self, uid, tx_uri):
		res_tx_uri = self.fconn.createOrUpdateNode(tx_uri + '/resources/SI/' + uid)
		res_uri = re.sub(r'/tx:[^\/]+/', '/', res_tx_uri)

		return (res_tx_uri, res_uri)


	def _guessFileExt(self, mimetype):
		ext = mimetypes.guess_extension(mimetype) or '.bin'
		cherrypy.log.error('Guessing MIME type for {}: {}'.format(mimetype, ext))
		return ext
