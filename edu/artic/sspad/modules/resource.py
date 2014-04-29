import abc, re
import cherrypy

from edu.artic.sspad.connectors.datagrinder_connector import DatagrinderConnector
from edu.artic.sspad.connectors.fedora_connector import FedoraConnector
from edu.artic.sspad.connectors.uidminter_connector import UidminterConnector

class Resource():
	''' Top-level class that handles resources. '''

	exposed = True

	def __init__(self):
		pass


	def mintUid(self, mid=None):
		return UidminterConnector().mintUid(self.pfx, mid)


	def openTransaction(self):
		return self.fconn.openTransaction()


	def createNodeInTx(self, uid, tx_uri):
		res_tx_uri = self.fconn.createOrUpdateNode(tx_uri + '/resources/SI/' + uid)
		#print('Image URI in tx:', img_tx_uri)
		res_uri = re.sub(r'/tx:[^\/]+/', '/', res_tx_uri)
		#print('Absolute image URI:', img_uri)
		return (res_tx_uri, res_uri)
