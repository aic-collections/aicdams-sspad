import mimetypes
import io
import json
import uuid

import cherrypy
import requests

from rdflib import URIRef, Literal

from sspad.config.datasources import lake_rest_api
from sspad.connectors.uidminter_connector import UidminterConnector
from sspad.modules.resource import Resource
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr


## Asset class.
#
#  This is the base class for all Assets.
class Asset(Resource):

	pfx = ''


	node_type = ns_collection['aic'].Asset


	## MIME type used for master generation.
	#
	#  @TODO Use another method to map MIME types to various generated datastreams.
	master_mimetype = 'image/jpeg'


	default_comment_type = 'general'


	## Properties as specified in requests.
	#
	#  These map to #prop_lake_names.
	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'legacy_uid', # String
			'batch_uid', # String
			'tag', # For insert: String, in the following format: <category>/<tag label> - For delete: String (tag URI)
			'comment', # For insert: Dict: {'type' : <String>, 'content' : <String>} - For delete: String (comment URI)
			#'has_ext_content',
			'citi_obj_pkey', # Integer
			'citi_obj_acc_no', # Integer
			'citi_agent_pkey', # Integer
			'citi_place_pkey', # Integer
			'citi_exhib_pkey', # Integer
			'pref_obj_pkey', # Integer
			'pref_agent_pkey', # Integer
			'pref_place_pkey', # Integer
			'pref_exhib_pkey', # Integer
		)


	## Tuples of LAKE namespaces and data types.
	#
	#  Data type string can be 'literal', 'uri' or 'variable'.
	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['aic'].legacyUid, 'literal'),
			(ns_collection['aic'].batchUid, 'literal'),
			(ns_collection['aic'].hasTag, 'uri'),
			(ns_collection['aic'].hasComment, 'uri'),
			#(ns_collection['fcrepo'].hasExternalContent, 'uri'),
			(ns_collection['aic'].represents, 'uri'),
			(ns_collection['aic'].represents, 'uri'),
			(ns_collection['aic'].represents, 'uri'),
			(ns_collection['aic'].represents, 'uri'),
			(ns_collection['aic'].represents, 'uri'),
			(ns_collection['aic'].isPrimaryRepresentationOf, 'uri'),
			(ns_collection['aic'].isPrimaryRepresentationOf, 'uri'),
			(ns_collection['aic'].isPrimaryRepresentationOf, 'uri'),
			(ns_collection['aic'].isPrimaryRepresentationOf, 'uri'),
		)


	## Request properties to resource prefix mapping.
	#  Keys are properties in prop_req_names. 
	#  Values are prefixes assigned to the resource that the Asset should be linked to
	reqprops_to_rels = {
		'citi_obj_pkey' : {'type' : ns_collection['aic'].Object, 'pfx' : 'OB'},
		'pref_obj_pkey' : {'type' : ns_collection['aic'].Object, 'pfx' : 'OB'},
		'citi_agent_pkey' : {'type' : ns_collection['aic'].Actor, 'pfx' : 'AC'},
		'pref_agent_pkey' : {'type' : ns_collection['aic'].Actor, 'pfx' : 'AC'},
		'citi_place_pkey' : {'type' : ns_collection['aic'].Place, 'pfx' : 'PL'},
		'pref_place_pkey' : {'type' : ns_collection['aic'].Place, 'pfx' : 'PL'},
		'citi_exhib_pkey' : {'type' : ns_collection['aic'].Event, 'pfx' : 'EV'},
		'pref_exhib_pkey' : {'type' : ns_collection['aic'].Event, 'pfx' : 'EV'},
	}


	@property
	def mixins(self):
		return super().mixins + (
			'aicmix:Derivable',
			'aicmix:Overlayable',
			'aicmix:Publ_Web',
		)


	## Path between the repo root and the asset node.
	@property
	def path(self):
		pfx = self.pfx + '/' if self.pfx else ''
		return 'resources/assets/' + pfx


	## GET method.
	#
	#  Lists all Assets or shows properties for an asset with given uid.
	#
	#  @param uid (string) UID of Asset to display.
	#
	#  @TODO stub
	def GET(self, uid=None, legacy_uid=None):

		self._setConnection()

		if uid:
			return {'message': '*stub* This is Asset #{}.'.format(uid)}
		elif legacy_uid:
			if self.tsconn.assert_node_exists_by_prop(ns_collection['aic'] + 'legacyUid', legacy_uid):
				return {'message': '*stub* This is Asset with legacy UID #{}.'.format(legacy_uid)}
			else:
				raise cherrypy.HTTPError(
					'404 Not Found',
					'An asset with this legacy UID does not exist.'
				)
		else:
			return {'message': '*stub* This is a list of Assets.'}


	## POST method.
	#
	#  Create a new Asset node with automatic UID by providing data and node properties.
	#
	#  @param mid			(string) Mid-prefix.
	#  @param properties	(dict) Properties to be associated with new node.
	#  @param **dstreams	(BytesIO) Arbitrary datastream(s).
	#  Name of the parameter is the datastream name.
	#  If the datastream is to be ingested directly into LAKE, the variable value is the actual data.
	#  If the datastream is in an external URL and must be a reference, 
	#  the variable name is prefixed with ref_ and the value is a URL (e.g. 'ref_source' will ingest a reference ds called 'source').
	#  Only the 'source' datastream is mandatory (or 'ref_source' if it is a reference).
	#
	#  @return (dict) Message with new node information.
	def POST(self, mid, properties='{}', overwrite=False, **dstreams):
		cherrypy.log('\n')
		cherrypy.log('************************')
		cherrypy.log('Begin ingestion process.')
		cherrypy.log('************************')
		cherrypy.log('')
		cherrypy.log('Properties: {}'.format(properties))

		self._setConnection()

		# If neither source nor ref_source is present, throw error
		if 'source' not in dstreams.keys() and 'ref_source' not in dstreams.keys():
			raise cherrypy.HTTPError('400 Bad Request', 'Required source datastream missing.')

		props = json.loads(properties)
		for p in props:
			# Wrap string props in one-element lists
			if not props[p].__class__.__name__ == 'list':
				props[p] = [props[p]]

		# Before anything else, check that if a legacy_uid parameter is
		# provied, no other Asset exists with that legacy UID. In the case one exists, 
		# the function shall return a '409 Conflict'.
		# The function assumes that multiple legacy UIDs can be assigned.
		if overwrite == False and 'legacy_uid' in props:
			for uid in props['legacy_uid']:
				if self.tsconn.assert_node_exists_by_prop(ns_collection['aic'] + 'uid', uid):
					raise cherrypy.HTTPError(
						'409 Conflict',
						'An asset with the same legacy UID already exists. Not creating a new one.'
					)

		# Create a new UID
		uid = self.mintUid(mid)

		if 'master' not in dstreams.keys() and 'ref_master' not in dstreams.keys():
			# Generate master if not present
			cherrypy.log('Master file not provided.')
			if 'ref_source' in dstreams.keys():
				cherrypy.log('Requesting {}...'.format(dstreams['ref_source']))
				req = requests.get(
					dstreams['ref_source'],
					headers={'Authorization' : self.auth_str}
				)
				req.raise_for_status()
				dstreams['master'] = self._generateMasterFile(req.content, uid + '_master.jpg')
			else:
				dstreams['master'] = self._generateMasterFile(
					self._getIOStreamFromReq(dstreams['source']),
					uid + '_master.jpg'
				)
		else:
			cherrypy.log('Master file provided.')

		# First validate all datastreams
		dsmeta = {}
		for dsname in dstreams.keys():
			ds = self._getIOStreamFromReq(dstreams[dsname])

			cherrypy.log('Validation round (' + dsname + '): class name: ' + ds.__class__.__name__)

			if dsname[:4] == 'ref_':
				cherrypy.log('Skipping validation for reference ds.')
			else:
				try:
					dsmeta[dsname] = self._validateDStream(ds, dsname)
					cherrypy.log('Validation for ' + dsname + ': ' + str(dsmeta[dsname]))
				except Exception as e:
					raise cherrypy.HTTPError(
						'415 Unsupported Media Type', 'Validation for datastream {} failed with exception: {}.'\
						.format(dsname, e)
					)

		# Open Fedora transaction
		self.tx_uri = self.lconn.openTransaction()
		#cherrypy.log('Created TX: {}'.format(self.tx_uri))

		try:
			# Create Asset node in tx
			self.uri_in_tx, self.uri = self.createNodeInTx(uid, self.tx_uri)

			# Set node properties
			init_tuples = self.base_prop_tuples + [
				(ns_collection['dc'].title, Literal(uid)),
				(ns_collection['aic'].uid, Literal(uid)),
			]

			cherrypy.log('Properties: {}'.format(properties))
			tuples = self._build_prop_tuples(insert_props=properties, init_insert_tuples=init_tuples)
			self._update_node(tuples)

			'''
			#cherrypy.log('Props available: {}'.format(list(prop_tuples)))
			for req_name, lake_name in self.props:
				#cherrypy.log('Req. name: {}; All prop names in request: {}'.format(req_name, props.keys()))
				if req_name in props.keys():
					#cherrypy.log('Req. name being parsed: {}'.format(req_name))
					
					# Build relationships
					rel_type = self.reqprops_to_rels[req_name] if req_name in self.reqprops_to_rels else {}

					for value in props[req_name]:
						if rel_type:
							value = self._add_mock_node_rel(self.tx_uri, rel_type, value)
							cherrypy.log('Ref URI in tx: {}'.format(value))
						prop_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

			#cherrypy.log('Props:' + str(prop_tuples))

			self.lconn.updateNodeProperties(self.uri_in_tx, insert_props=prop_tuples)
			'''

			# Loop over all datastreams and ingest them
			for dsname in dstreams.keys():

				if dsname[:4] == 'ref_':
					# Create a reference node.
					in_dsname = dsname [4:]
					cherrypy.log('Creating a reference ds with name: aic:ds_{}'.format(in_dsname))
					ds_content_uri = self.lconn.createOrUpdateRefDStream(
						self.uri_in_tx + '/aic:ds_' + in_dsname,
						dstreams[dsname]
					)
				else:
					in_dsname = dsname
					cherrypy.log('Ingestion round (' + in_dsname + '): class name: ' + ds.__class__.__name__)
					# Create an actual datastream.
					ds = self._getIOStreamFromReq(dstreams[dsname])
					ds.seek(0)
					ds_content_uri = self.lconn.createOrUpdateDStream(
						self.uri_in_tx + '/aic:ds_' + dsname,
						ds = ds,
						dsname = uid + '_' + in_dsname + \
								self._guessFileExt(dsmeta[dsname]['mimetype']),
						mimetype = dsmeta[dsname]['mimetype']
					)

				ds_meta_uri = ds_content_uri + '/fcr:metadata'

				# Set source datastream properties
				prop_tuples = [
					(ns_collection['dc'].title, Literal(uid + '_' + in_dsname)),
				]
				if dsname == 'master':
					prop_tuples.append(
						(ns_collection['rdf'].type, ns_collection['aicmix'].MasterDStream)
					)
				else:
					prop_tuples.append(
						(ns_collection['rdf'].type, ns_collection['aicmix'].Datastream)
					)

				self.lconn.updateNodeProperties(ds_meta_uri, insert_props=prop_tuples)
		except:
			# Roll back transaction if something goes wrong
			#self.lconn.rollbackTransaction(self.tx_uri)
			raise

		# Commit transaction
		self.lconn.commitTransaction(self.tx_uri)

		cherrypy.response.status = 201
		cherrypy.response.headers['Location'] = self.uri

		return {"message": "Asset created.", "data": {"location": res_uri}}


	## PUT method.
	#
	#  Adds or replaces datastreams or replaces the whole property set of an Asset.
	#
	#  @param uid		(string) Asset UID.
	#  @param properties	(dict) Properties to be associated with new node.
	#  @param **dstreams	(BytesIO) Arbitrary datastream(s). Name of the parameter is the datastream name.
	#  Only the 'source' datastream is mandatory.
	#
	#  @return (dict) Message with node information.
	#
	#  @TODO Replacing property set is not supported yet, and might not be needed anyway.
	def PUT(self, uid=None, uri=None, properties={}, **dstreams):

		self._setConnection()
		self._set_uri(uri, uid)

		dsnames = sorted(dstreams.keys())
		for dsname in dsnames:
			ds = _getIOStreamFromReq(dstreams[dsname])
			src_format, src_size, src_mimetype = self._validateDStream(ds)

			#cherrypy.log('UID: ' + uid + '; dsname: ' + dsname + ' mimetype: ' + src_mimetype)
			#cherrypy.log('mimetype guess: ' + self._guessFileExt(src_mimetype))
			#ds.seek(0)
			with ds.read() as src_data:
				content_uri = self.lconn.createOrUpdateDStream(
					self.uri + '/aic:ds_' + dsname,
					ds=src_data,
					dsname = uid + '_' + dsname + self._guessFileExt(src_mimetype),
					mimetype = src_mimetype
				)

				if dsname == 'source' and 'master' not in dsnames:
					# Recreate master file automatically if source is provided
					# without master
					cherrypy.log('No master file provided with source, re-creating master.')
					cherrypy.log('DS: '+str(ds))
					master = self._generateMasterFile(src_data, uid + '_master.jpg')
					content_uri = self.lconn.createOrUpdateDStream(
						self.uri + '/aic:ds_master',
						ds=master.read(),
						dsname = uid + '_master' + self._guessFileExt(self.master_mimetype),
						mimetype = self.master_mimetype
					)
				src_data = None # Flush datastream

		return {"message": "Resource updated.", "data": {"location": self.uri}} # @TODO Actually verify the URI from response headers.


	## PATCH method.
	#
	#  Adds or removes properties and mixins in an Asset.
	#
	#  @param uid				(string) Asset UID.
	#  @param insert_props	(dict) Properties to be inserted.
	#  @param delete_props	(dict) Properties to be deleted.
	def PATCH(self, uid=None, uri=None, insert_props='{}', delete_props='{}'):

		self._setConnection()
		self._set_uri(uri, uid)

		try:
			insert_props = json.loads(insert_props)
			delete_props = json.loads(delete_props)
		except:
			raise cherrypy.HTTPError(
				'400 Bad Request',
				'Properties are invalid. Please review your request.'
			)

		#cherrypy.log('Insert props:' + str(insert_props))
		#cherrypy.log('Delete props:' + str(delete_props))

		# Open Fedora transaction
		self.tx_uri = self.lconn.openTransaction()

		# Collect properties
		try:
			tuples = self._build_prop_tuples(
				insert_props=insert_props,
				delete_props=delete_props
			)
			self._update_node(tuples)
		except:
			self.lconn.rollbackTransaction(self.tx_uri)
			raise

		self.lconn.commitTransaction(self.tx_uri)

		cherrypy.response.status = 204
		cherrypy.response.headers['Location'] = self.uri # @TODO Actually verify the URI from response headers.

		return {"message": "Asset updated."}


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


	def _set_uri(self, uri=None, uid=None, legacy_uid=None):
		'''Validates the existence of a node from provided URI, UID or legacy UID
		and set #uri to a value according to the first valid one found.'''

		if not uri and not uid and not legacy_uid:
			raise ValueError('No valid identifier provided.')

		if uri and self.lconn.assert_node_exists(uri):
			self.uri = uri
			return True

		check_prop = ns_collection['aic'] + 'uid' \
				if uid \
				else ns_collection['aic'] + 'legacyUid'
		check_uid = uid if uid else legacy_uid
		check_uri = self.tsconn.get_node_uri_by_prop(check_prop, check_uid)
		
		if check_uri:
			self.uri = check_uri
			return True
		else:
			return False


	## Normalize the behaviour of a datastream object regardless of its source.
	#
	#  If ds is a byte stream instead of a Part instance, wrap it in an
	#  anonymous object as a 'file' property.
	#
	#  @param ds The BytesIO or bytes object to be normalized.
	def _getIOStreamFromReq(self, ds):
		if hasattr(ds, 'file'):
			cherrypy.log('Normalizer: ds.file exists already and is of class type {}.'.format(
				ds.file.__class__.__name__
			))
			return ds.file
		elif ds.__class__.__name__ == 'bytes':
			cherrypy.log('Normalizer: got a bytestream.')
			return io.BytesIO(ds)
		elif ds.__class__.__name__ == 'BytesIO':
			cherrypy.log('Normalizer: got a BytesIO.')
			return ds


	def _build_prop_tuples(
			self, insert_props={}, delete_props={}, init_insert_tuples=[]
			):
		''' Build delete, insert and where tuples suitable for #LakeConnector:updateNodeProperties.
		from a list of insert and delete properties.
		Also builds a list of nodes that need to be deleted and/or inserted to satisfy references.
		'''

		insert_tuples = init_insert_tuples
		delete_tuples, where_tuples = ([],[])
		insert_nodes, delete_nodes = ({},{})

		for req_name, lake_name in self.props:

			# Delete tuples + nodes
			if req_name in delete_props:
				if isinstance(delete_props[req_name], list):
					# Delete one or more values from property
					for value in delete_props[req_name]:
						if req_name == 'tag':
							value = lake_rest_api['tags_base_url'] + value
						elif req_name == 'comment':
							delete_nodes['comments'] = delete_props['comment']
						delete_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

				elif delete_props[req_name] == '':
					# Delete the whole property
					delete_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
					where_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
			
			# Insert tuples + nodes
			if req_name in insert_props:
				for value in insert_props[req_name]:
					# Check if property is a relationship
					if req_name in self.reqprops_to_rels:
						rel_type = self.reqprops_to_rels[req_name]
						ref_uri = '{}/resources/holders/{}/{}-{}'.format(self.tx_uri, rel_type['pfx'], rel_type['pfx'], value)
						#@TODO Implement after collections-shared DB is federated
						#if not self.lconn.assert_node_exists(ref_uri):
						#	raise cherrypy.HTTPError(
						#		'409 Conflict',
						#		'Referenced node {} does not exist. Cannot create relationship.'.format(ref_uri)
						#	)
						value = ref_uri
					elif req_name == 'tag':
						insert_nodes['tags'] = insert_props['tag']
						#value = lake_rest_api['tags_base_url'] + value
						continue
					elif req_name == 'comment':
						insert_nodes['comments'] = insert_props['comment']
						continue
					cherrypy.log('Value for {}: {}'.format(req_name, value))
					insert_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

		return {
			'nodes' : (delete_nodes, insert_nodes),
			'tuples' : (delete_tuples, insert_tuples, where_tuples),
		}


	def _update_node(self, tuples):
		'''Updates a node inserting and deleting related nodes if necessary,'''

		delete_nodes, insert_nodes = tuples['nodes']
		delete_tuples, insert_tuples, where_tuples = tuples['tuples']

		for node_type in delete_nodes.keys():
			for uri in delete_nodes[node_type]:
				self.lconn.delete_node(uri)

		for node_type in insert_nodes.keys():
			if node_type == 'comment':
				for comment in insert_nodes[node_type]:
					comment_uri = self.lconn.createOrUpdateNode(
						self.uri + '/aic:annotations/' + uuid.uuid4(),
						props = {
							'content' : comment['content'],
							'type' : comment['type'] if 'type' in comment else self.default_comment_type,
						}
					)
					

		self.lconn.updateNodeProperties(
			self.uri,
			delete_props=delete_tuples,
			insert_props=insert_tuples,
			where_props=where_tuples
		)

		# Add comment nodes
		if 'comment' in insert_props and insert_props['comment']:
			self._insert_comments(url, insert_props['comment'])



#	def _add_mock_node_rel(self, base_uri, rel_type, rel_value):
#		''' Add a relationship with a federated CITI entity.
#		If the node does not exist yet, create a mock one.
#		ONLY FOR TESTING!
#		'''
#
#		cherrypy.log('Relationship type: {}'.format(rel_type))
#		cherrypy.log('value: {}'.format(rel_value))
#		ref_uri = '{}/resources/holders/{}/{}-{}'.format(base_uri, rel_type['pfx'], rel_type['pfx'], rel_value)
#
#		if not self.lconn.assert_node_exists(ref_uri):
#			cherrypy.log('Creating ref node.')
#			ref_uri_res = self.lconn.createOrUpdateNode(ref_uri)
#			self.lconn.updateNodeProperties(ref_uri_res, insert_props=[
#				(ns_collection['rdf'].type, URIRef(rel_type['type'])),
#				(ns_collection['aic'].uid, Literal(rel_value))
#			])
#			return ref_uri_res
#		else:
#			cherrypy.log('Ref node exists.')
#			return ref_uri

	
	## Adds one or more comments.
	#
	#  @param subject (string) URI of asset that annotation is referring to.
	#  @param comments (list) Comment contents. Author and creation date will be added
	#  by Fedora from request headers and timestamp.
	def _insert_comments(self, subject, comments):
		for comment in comments:
			comment_uri = self.lconn.createOrUpdateNode(
				url + '/aic:annotations/' + uuid.uuid4(),
				props = {
					'content' : comment['content'],
					'type' : comment['type'] if 'type' in comment else self.default_comment_type,
				}
			)

			self.lconn.updateNodeProperties(
				subject,
				insert_tuples = (
					(self.props['comment'][0], self._rdfObject(comment_uri, 'uri'))
				)
			)

	
