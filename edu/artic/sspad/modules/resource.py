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
		('image/jpeg', '.jpeg'),
		('image/psd', '.psd'),
		('image/vnd.adobe.photoshop', '.psd'),
		('image/x-psd', '.psd'),
		# [...]
	]

	def __init__(self):
		for mt, ext in self.add_mimetypes:
			mimetypes.add_type(mt, ext)


	def _setConnection(self):
		# Set connectors - @TODO move this in __init__ method of super class
		# when you figure out how to access cherrypy.request.headers there
		self.auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.fconn = FedoraConnector(self.auth_str)
		self.dgconn = DatagrinderConnector(self.auth_str)
		self.tsconn = TstoreConnector(self.auth_str)


	def mintUid(self, mid=None):
		return UidminterConnector().mintUid(self.pfx, mid)


	def openTransaction(self):
		return self.fconn.openTransaction()


	def createNodeInTx(self, uid, tx_uri):
		res_tx_uri = self.fconn.createOrUpdateNode(tx_uri + '/resources/SI/' + uid)
		res_uri = re.sub(r'/tx:[^\/]+/', '/', res_tx_uri)

		return (res_tx_uri, res_uri)


	def _guessFileExt(self, mimetype):
		return mimetypes.guess_extension(mimetype) or ''
