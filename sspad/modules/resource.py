import abc, mimetypes, re
import cherrypy

from sspad.resources.rdf_lexicon import ns_collection, ns_mgr
from sspad.connectors.datagrinder_connector import DatagrinderConnector
from sspad.connectors.lake_connector import LakeConnector
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.connectors.uidminter_connector import UidminterConnector

## Resource class.
#  This is the base class for all resource operations.
class Resource():

	## Short-hand namespace variables.
	ns_aic, ns_aicmix, ns_dc, ns_rdf, ns_indexing =\
		ns_collection['aic'],\
		ns_collection['aicmix'],\
		ns_collection['dc'],\
		ns_collection['rdf'],\
		ns_collection['indexing']


	## Tuples of LAKE namespaces and data types.
	#
	#  Data type string can be 'literal', 'uri' or 'variable'.
	prop_lake_names = (
		(ns_rdf.type, 'uri'),
		(ns_dc.title, 'literal'),
		(ns_aic.legacyUid, 'literal'),
		(ns_aic.batchUid, 'literal'),
		(ns_aic.citiObjUid, 'literal'),
		(ns_aic.citiObjAccNo, 'literal'),
		(ns_aic.citiAgentUid, 'literal'),
		(ns_aic.citiPlaceUid, 'literal'),
		(ns_aic.citiExhibUid, 'literal'),
		(ns_aic.citiImgDBankUid, 'literal'),
	)

	## Properties as specified in requests.
	#
	#  These map to #prop_lake_names.
	prop_req_names = (
		'type',
		'title',
		'legacy_uid',
		'batch_uid',
		'citi_obj_pkey',
		'citi_obj_acc_no',
		'citi_agent_pkey',
		'citi_place_pkey',
		'citi_exhib_pkey',
		'citi_imgdbank_pkey',
	)


	## Mix-ins considered for updating.
	mixins = (
		'aicmix:citiPrivate',
		'aicmix:derivable',
		'aicmix:overlaid',
		'aicmix:publ_web',
	)


	## Resource prefix.
	#
	#  This is used in the node UID and designates the resource type.
	#  It is mandatory to define it for each resource type.
	#  @TODO Call uidminter and generate a (cached) map of pfx to Resource subclass names.
	pfx=''


	## RDF type.
	#
	#  This is a URI that reflects the node type set in the LAKE CND.
	#
	#  @sa https://github.com/aic-collections/aicdams-lake/tree/master-aic/fcrepo-webapp/src/aic/resources/cnd
	node_type=ns_aic.resource


	## Additional MIME types.
	#
	#  They are added to the known list for guessing file extensions.
	_add_mimetypes = (
		('image/jpeg', '.jpeg', True),
		('image/psd', '.psd', False),
		('image/vnd.adobe.photoshop', '.psd', True),
		('image/x-psd', '.psd', False),
		# [...]
	)


	## Class constructor.
	#
	#  Sets up several connections and MIME types.
	def __init__(self):
		#self._setConnection()

		if not mimetypes.inited:
			mimetypes.init()
			for mt, ext, strict in self._add_mimetypes:
				mimetypes.add_type(mt, ext, strict)


	## Sets up connections to external services.
	def _setConnection(self):
		'''Set connectors.'''

		print('Setting up connections.')
		self.auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.fconn = LakeConnector(self.auth_str)
		self.dgconn = DatagrinderConnector(self.auth_str)
		self.tsconn = TstoreConnector(self.auth_str)


	## Calls an eternal service to generate and returns a UID.
	#
	#  @param mid		(string) Second prefix needed for certain types.
	#  @return string Generated UID.
	def mintUid(self, mid=None):
		try:
			uid = UidminterConnector().mintUid(self.pfx, mid)
		except:
			raise RuntimeError('Could not generate UID.')
		return uid


	## Opens a transaction in LAKE.
	def openTransaction(self):
		return self.fconn.openTransaction()


	## Creates a node within a transaction in LAKE.
	#
	#  @param uid		(string) UID of the node to be generated.
	#  @param tx_uri	(string) URI of the transaction.
	#
	#  @return tuple Two resource URIs: one in the transaction and one outside of it.
	def createNodeInTx(self, uid, tx_uri):
		res_tx_uri = self.fconn.createOrUpdateNode('{}/resources/{}/{}'.format(tx_uri,self.pfx,uid))
		res_uri = re.sub(r'/tx:[^\/]+/', '/', res_tx_uri)

		return (res_tx_uri, res_uri)


	## Guesses file extension from MIME types.
	#
	#  @param mimetype	(string) MIME type, such as 'image/jpeg'
	#
	#  @return string Extetnsion guessed (including leading period)
	def _guessFileExt(self, mimetype):
		ext = mimetypes.guess_extension(mimetype) or '.bin'
		cherrypy.log.error('Guessing MIME type for {}: {}'.format(mimetype, ext))
		return ext
