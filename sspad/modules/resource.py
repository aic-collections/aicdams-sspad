import mimetypes
import re

import cherrypy

from urllib.parse import urlparse

from sspad.connectors.datagrinder_connector import DatagrinderConnector
from sspad.connectors.lake_connector import LakeConnector
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.connectors.uidminter_connector import UidminterConnector
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr

## Resource class.
#  This is the base class for all resource operations.
class Resource():

	exposed = True


	## Resource prefix.
	#
	#  This is used in the node UID and designates the resource type.
	#  It is mandatory to define it for each resource type.
	#  @TODO Call uidminter and generate a (cached) map of pfx to Resource subclass names.
	pfx = ''


	## RDF type.
	#
	#  This is a URI that reflects the node type set in the LAKE CND.
	#
	#  @sa https://github.com/aic-collections/aicdams-lake/tree/master-aic/fcrepo-webapp/src/aic/resources/cnd
	node_type = ns_collection['aic'].resource


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


	## Tuples of LAKE namespaces and data types.
	#
	#  Data type string can be 'literal', 'uri' or 'variable'.
	@property
	def prop_lake_names(self):
		return (
			(ns_collection['rdf'].type, 'uri'),
			(ns_collection['dc'].title, 'literal'),
		)


	## Properties as specified in requests.
	#
	#  These map to #prop_lake_names.
	@property
	def prop_req_names(self):
		return (
			'type',
			'title',
		)


	## Mix-ins considered for updating.
	@property
	def mixins(self):
		return (
			'aicmix:citi',
			'aicmix:citiPrivate',
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
		self.lconn = LakeConnector(self.auth_str)
		self.dgconn = DatagrinderConnector(self.auth_str)
		self.tsconn = TstoreConnector(self.auth_str)


	## Opens a transaction in LAKE.
	def openTransaction(self):
		return self.lconn.openTransaction()


	## Creates a node within a transaction in LAKE.
	#
	#  @param uid		(string) UID of the node to be generated.
	#  @param tx_uri	(string) URI of the transaction.
	#
	#  @return tuple Two resource URIs: one in the transaction and one outside of it.
	def createNodeInTx(self, uid, tx_uri):
		res_tx_uri = self.lconn.createOrUpdateNode('{}/{}{}'.format(tx_uri,self.path,uid))
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


	## Validate a datastream.
	#
	#  Override this method for each resource subclass.
	def _validateDStream(self, ds, dsname='', rules={}):
		pass


	## Returns a RDF triple object from a value and a type.
	#
	#  The value must be in the #mixins list.
	#  Depending on the value of @p type, a literal object, a URI or a variable (?var) is created.
	#
	#  @param value		(string) Value to be processed.
	#  @oaram type		(string) One of 'literal', 'uri', 'variable'.
	#
	#  @return (rdflib.URIRef | rdflib.Literal | rdflib.Variable) rdflib object.
	def _rdfObject(self, value, type):
			cherrypy.log('Value: ' + str(value))
			if type == 'literal':
					return Literal(value)
			elif type == 'uri':
				parsed_uri = urlparse(value)
					if parsed_uri.scheme and parsed_uri.netloc:
						return URIRef(value)
					elif ':' in value:
						ns, tname = value.split(':')
						if ns not in ns_collection or value not in self.mixins:
							cherrypy.HTTPError(
									'400 Bad Request', 'Relationship {} cannot be added or removed with this method.'.format(value))
						return URIRef(ns_collection[ns] + tname)
					else
						raise ValueError('Value {} is not a valid fully-qualified or namespace-prefixed URI.'.format(value))
			elif type == 'variable':
					return Variable(value)


