import mimetypes
import io
import json
import os
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
			'comment', # For insert: Dict: {'cat' : <String>, 'content' : <String>} - For delete: String (comment URI)
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
			'has_master', # String (uri)
			'has_instance', # String (uri)
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
			(ns_collection['aic'].hasMaster, 'uri'),
			(ns_collection['aic'].hasInstance, 'uri'),
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



	## HTTP-EXPOSED METHODS ##

	## GET method.
	#
	#  Lists all Assets or shows properties for an asset with given uid.
	#
	#  @param uid (string) UID of Asset to display.
	#
	#  @TODO stub
	def GET(self, uid=None, legacy_uid=None):

		self._set_connection()

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
	#  @param props	(dict) Properties to be associated with new node.
	#  @param **dstreams	(BytesIO) Arbitrary datastream(s).
	#  Name of the parameter is the datastream name.
	#  If the datastream is to be ingested directly into LAKE, the variable value is the actual data.
	#  If the datastream is in an external URL and must be a reference, 
	#  the variable name is prefixed with ref_ and the value is a URL (e.g. 'ref_source' will ingest a reference ds called 'source').
	#  Only the 'source' datastream is mandatory (or 'ref_source' if it is a reference).
	#
	#  @return (dict) Message with new node information.
	def POST(self, mid, props='{}', **dstreams):
		cherrypy.log('\n')
		cherrypy.log('************************')
		cherrypy.log('Begin ingestion process.')
		cherrypy.log('************************')
		cherrypy.log('')

		self._set_connection()

		props_dict = json.loads(props)

		return self.create(mid, props_dict, **dstreams)


	## PUT method.
	#
	#  Adds or replaces datastreams or replaces the whole property set of an Asset.
	#
	#  @param uid		(string) Asset UID. Specify this or 'uri' only if the node is known to exist,
	#	  otherwise a 404 Not Found will be thrown.
	#  @param uri		(string) Asset URI. If this is not provided, node will be searched by UID.
	#  @param props	(dict) Properties to be associated with new or updated node. 
	#	  The 'legacy_uid' property is searched for conflicts or to find nodes when neither 'uri' or 'uid' are known.
	#  @param **dstreams	(BytesIO) Arbitrary datastream(s). Name of the parameter is the datastream name.
	#  Only the 'source' datastream is mandatory.
	#
	#  @return (dict) Message with node information.
	#
	#  @TODO Replacing property set is not supported yet, and might not be needed anyway.
	def PUT(self, uid=None, uri=None, props='{}', **dstreams):

		cherrypy.log('\n')
		cherrypy.log('************************')
		cherrypy.log('Begin update process.')
		cherrypy.log('************************')
		cherrypy.log('')

		self._set_connection()

		props_dict = json.loads(props)

		legacy_uid = props_dict['legacy_uid'] if 'legacy_uid' in props_dict else None
		self._set_uri(uri, uid, legacy_uid)

		if not self.uri:
			return self.create('', props_dict, **dstreams)
			#raise cherrypy.HTTPError('404 Not Found', 'Node was not found for updating.')

		self._check_uid_dupes(uid, legacy_uid)
		return self.update(uid, None, props_dict, **dstreams)

	
	## PATCH method.
	#
	#  Adds or removes properties and mixins in an Asset.
	#
	#  @param uid				(string) Asset UID.
	#  @param insert_props	(dict) Properties to be inserted.
	#  @param delete_props	(dict) Properties to be deleted.
	def PATCH(self, uid=None, uri=None, insert_props='{}', delete_props='{}'):

		self._set_connection()
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
		self.tx_uri = self.lconn.open_transaction()
		self.uri_in_tx = self.uri.replace(lake_rest_api['base_url'], tx_uri + '/')

		# Collect properties
		try:
			tuples = self._build_prop_tuples(
				insert_props=insert_props,
				delete_props=delete_props
			)
			self._update_node(self.uri_in_tx, tuples)
		except:
			self.lconn.rollbackTransaction(self.tx_uri)
			raise

		self.lconn.commitTransaction(self.tx_uri)

		cherrypy.response.status = 204
		cherrypy.response.headers['Location'] = self.uri # @TODO Actually verify the URI from response headers.

		return {"message": "Asset updated."}



	## NON-EXPOSED METHODS ##

	def create(self, mid, props={}, **dstreams):
		'''Create an asset. @sa POST'''

		# If neither source nor ref_source is present, throw error
		if 'source' not in dstreams.keys() and 'ref_source' not in dstreams.keys():
			raise cherrypy.HTTPError('400 Bad Request', 'Required source datastream missing.')

		# Wrap string props in one-element lists
		for p in props:
			if not props[p].__class__.__name__ == 'list':
				props[p] = [props[p]]

		# Before anything else, check that if a legacy_uid parameter is
		# provied, no other Asset exists with that legacy UID. In the case one exists, 
		# the function shall return a '409 Conflict'.
		# The function assumes that multiple legacy UIDs can be assigned.
		if 'legacy_uid' in props:
			for uid in props['legacy_uid']:
				if self.tsconn.assert_node_exists_by_prop(ns_collection['aic'] + 'legacyUid', uid):
					raise cherrypy.HTTPError(
						'409 Conflict',
						'An asset with the same legacy UID already exists. Cannot create a new one.'
					)

		# Create a new UID
		uid = self.mint_uid(mid)

		# Generate master if not existing
		dstreams = self._generate_master(dstreams)

		# First validate all datastreams
		dsmeta = self._validate_dstreams(dstreams)

		# Open Fedora transaction
		self.tx_uri = self.lconn.open_transaction()
		#cherrypy.log('Created TX: {}'.format(self.tx_uri))

		try:
			# Create Asset node in tx
			self.uri_in_tx, self.uri = self.create_node_in_tx(uid, self.tx_uri)
			cherrypy.log('Node URI in TX: {}; outslide of TX: {}'.format(self.uri_in_tx, self.uri))

			# Set node props
			init_tuples = self.base_prop_tuples + [
				(ns_collection['dc'].title, Literal(uid)),
				(ns_collection['aic'].uid, Literal(uid)),
			]
			cherrypy.log('Init tuples: {}'.format(init_tuples))

			cherrypy.log('Properties: {}'.format(props))
			tuples = self._build_prop_tuples(insert_props=props, init_insert_tuples=init_tuples)
			self._update_node(self.uri_in_tx, tuples)

			# Loop over all datastreams and ingest them
			self._ingest_instances(dstreams, dsmeta)

		except:
			# Roll back transaction if something goes wrong
			#self.lconn.rollbackTransaction(self.tx_uri)
			raise

		# Commit transaction
		self.lconn.commitTransaction(self.tx_uri)

		cherrypy.response.status = 201
		cherrypy.response.headers['Location'] = self.uri

		return {"message": "Asset created.", "data": {"location": self.uri}}


	def update(self, uid=None, uri=None, props='{}', **dstreams):
		'''Updates an asset. @sa PUT'''

		#self._set_connection()
		dsnames = sorted(dstreams.keys())
		for dsname in dsnames:
			ds = _get_iostream_from_req(dstreams[dsname])
			src_format, src_size, src_mimetype = self._validate_datastream(ds)

			#cherrypy.log('UID: ' + uid + '; dsname: ' + dsname + ' mimetype: ' + src_mimetype)
			#cherrypy.log('mimetype guess: ' + self._guess_file_ext(src_mimetype))
			#ds.seek(0)
			with ds.read() as src_data:
				content_uri = self.create_or_update_instance(
					parent_uri = self.uri,
					name = dsname,
					ds = src_data,
					mimetype = src_mimetype
				)

				if dsname == 'source' and 'master' not in dsnames:
					# Recreate master file automatically if source is provided
					# without master
					cherrypy.log('No master file provided with source, re-creating master.')
					cherrypy.log('DS: '+str(ds))
					master = self._generateMasterFile(src_data, uid + '_master.jpg')
					content_uri = self.create_or_update_instance(
						parent_uri = self.uri,
						name = dsname,
						ds=master.read(),
						mimetype = self.master_mimetype
					)
				src_data = None # Flush datastream

		return {"message": "Resource updated.", "data": {"location": self.uri}} # @TODO Actually verify the URI from response headers.


	## Calls an eternal service to generate and returns a UID.
	#
	#  @param mid		(string) Second prefix needed for certain types.
	#  @return string Generated UID.
	def mint_uid(self, mid=None):
		try:
			self.uid = UidminterConnector().mint_uid(self.pfx, mid)
		except:
			raise RuntimeError('Could not generate UID.')
		return self.uid


	def _set_uri(self, uri=None, uid=None, legacy_uid=None):
		'''Validates the existence of a node from provided URI, UID or legacy UID
		and set #uri to a value according to the first valid one found.
		'''

		if not uri and not uid and not legacy_uid:
			raise ValueError('No valid identifier provided.')

		self.uri = None

		# First check the URI.
		if uri:
			if self.lconn.assert_node_exists(uri):
				self.uri = uri
				return True
			else:
				raise cherrypy.HTTPError('404 Not Found', 'No node with the provided URI: {}'.format(uri))

		# If no URI is provided, check UID and legacy UID, in that order.
		if uid:
			check_prop = ns_collection['aic'] + 'uid'
			check_uid = uid
			self.uid = uid
		else:
			ns_collection['aic'] + 'legacyUid'
			check_uid = legacy_uid

		check_uri = self.tsconn.get_node_uri_by_prop(check_prop, check_uid)
		
		if check_uri:
			self.uri = check_uri
			return True
		else:
			return False


	def _check_uid_dupes(self, uid=None, legacy_uid=None):
		'''Checks if a node with a given UID or a given legacy UID exists.'''

		if not uid and not legacy_uid:
			raise ValueError('Neither uid or legacy_uid were provided. Cannot check for duplicates.')

		if uid:
			uri_uid = self.tsconn.find_node_uri_by_prop(ns_collection['aic'] + 'uid', uid)
			if not self.uri == uri_uid:
				cherrypy.response.headers['link'] = uri_uid
				raise cherrypy.HTTPError('409 Conflict', 'A node with UID {} exsists already.'.format(uri))
		if legacy_uid:
			uri_legacy_uid = self.tsconn.find_node_uri_by_prop(ns_collection['aic'] + 'legacyUid', legacy_uid)
			if not self.uri == uri_legacy_uid:
				cherrypy.response.headers['link'] = legacy_uri_uid
				raise cherrypy.HTTPError('409 Conflict', 'A node with legacy UID {} exsists already.'.format(legacy_uri))

		return True


	def _generate_master(self, dstreams):
		'''Generates master datastream from source if missing and returns the complete list of datastreams.'''
		if 'master' not in dstreams.keys() and 'ref_master' not in dstreams.keys():
			# Generate master if not present
			cherrypy.log('Master file not provided.')
			if 'ref_source' in dstreams.keys():
				cherrypy.log('Requesting {}...'.format(dstreams['ref_source']))
				ds_binary = self.lconn.get_binary_stream(dstreams['ref_source'])

				dstreams['master'] = self._generateMasterFile(ds_binary.content, self.uid + '_master.jpg')
			else:
				dstreams['master'] = self._generateMasterFile(
					self._get_iostream_from_req(dstreams['source']),
					self.uid + '_master.jpg'
				)
		else:
			cherrypy.log('Master file provided.')

		return dstreams


	def _validate_dstreams(self, dstreams):
		dsmeta = {}
		for dsname in dstreams.keys():
			ds = self._get_iostream_from_req(dstreams[dsname])

			cherrypy.log('Validation round (' + dsname + '): class name: ' + ds.__class__.__name__)

			if dsname[:4] == 'ref_':
				cherrypy.log('Skipping validation for reference ds.')
			else:
				try:
					dsmeta[dsname] = self._validate_datastream(ds, dsname)
					cherrypy.log('Validation for ' + dsname + ': ' + str(dsmeta[dsname]))
				except Exception as e:
					raise cherrypy.HTTPError(
						'415 Unsupported Media Type', 'Validation for datastream {} failed with exception: {}.'\
						.format(dsname, e)
					)

		return dsmeta


	## Normalize the behaviour of a datastream object regardless of its source.
	#
	#  If ds is a byte stream instead of a Part instance, wrap it in an
	#  anonymous object as a 'file' property.
	#
	#  @param ds The BytesIO or bytes object to be normalized.
	def _get_iostream_from_req(self, ds):
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
			self, insert_props={}, delete_props={}, init_insert_tuples=[], ignore_broken_rels=True
			):
		''' Build delete, insert and where tuples suitable for #LakeConnector:update_node_properties.
		from a list of insert and delete properties.
		Also builds a list of nodes that need to be deleted and/or inserted to satisfy references.
		'''

		#cherrypy.log('Initial insert tuples: {}.'.format(init_insert_tuples))
		insert_tuples = init_insert_tuples
		delete_tuples, where_tuples = ([],[])
		insert_nodes, delete_nodes = ({},{})

		for req_name in self.props.keys():
			lake_name = self.props[req_name]

			# Delete tuples + nodes
			if req_name in delete_props:
				if isinstance(delete_props[req_name], list):
					# Delete one or more values from property
					for value in delete_props[req_name]:
						if req_name == 'tag':
							delete_nodes['tags'] = delete_props['tag']
							#value = lake_rest_api['tags_base_url'] + value
						elif req_name == 'comment':
							delete_nodes['comments'] = delete_props['comment']
						delete_tuples.append((lake_name[0], self._build_rdf_object(value, lake_name[1])))

				elif delete_props[req_name] == '':
					# Delete the whole property
					delete_tuples.append((lake_name[0], self._build_rdf_object('?' + req_name, 'variable')))
					where_tuples.append((lake_name[0], self._build_rdf_object('?' + req_name, 'variable')))
			
			# Insert tuples + nodes
			if req_name in insert_props:
				cherrypy.log('Adding req. name {} from insert_props {}...'.format(req_name, insert_props))
				cherrypy.log('Insert props: {}'.format(insert_props.__class__.__name__))
				for value in insert_props[req_name]:
					# Check if property is a relationship
					if req_name in self.reqprops_to_rels:
						rel_type = self.reqprops_to_rels[req_name]
						ref_uri = self.tsconn.get_node_uri_by_prop(ns_collection['aicdb'] + 'citi_pkey', value)
						if not ref_uri:
							if ignore_broken_rels:
								continue
							else:
								raise cherrypy.HTTPError(
									'404 Not Found',
									'Referenced CITI resource with CITI Pkey {} does not exist. Cannot create relationship.'.format(value)
								)
						value = ref_uri
					elif req_name == 'tag':
						insert_nodes['tags'] = insert_props['tag']
						#value = lake_rest_api['tags_base_url'] + value
						continue
					elif req_name == 'comment':
						insert_nodes['comments'] = insert_props['comment']
						continue
					cherrypy.log('Value for {}: {}'.format(req_name, value))
					insert_tuples.append((lake_name[0], self._build_rdf_object(value, lake_name[1])))

		return {
			'nodes' : (delete_nodes, insert_nodes),
			'tuples' : (delete_tuples, insert_tuples, where_tuples),
		}


	def _ingest_instances(self, dstreams, dsmeta):
		'''Loops over datastreams and ingests them within a transaction.'''

		cherrypy.log('DSmeta: {}'.format(dsmeta))
		for dsname in dstreams.keys():

			if dsname[:4] == 'ref_':
				# Create a reference node.
				in_dsname = dsname [4:]
				cherrypy.log('Creating a reference ds with name: aic:ds_{}'.format(in_dsname))
				ds_content_uri = self.create_or_update_instance(
					parent_uri = self.uri_in_tx,
					name = in_dsname,
					ref = dstreams[dsname]
				)
			else:
				in_dsname = dsname
				#cherrypy.log('Ingestion round (' + in_dsname + '): class name: ' + dstreams[dsname].__class__.__name__)
				# Create an actual datastream.
				ds = self._get_iostream_from_req(dstreams[dsname])
				ds.seek(0)
				ds_content_uri = self.create_or_update_instance(
					parent_uri = self.uri_in_tx,
					name = in_dsname,
					ds = ds,
					mimetype = dsmeta[dsname]['mimetype']
				)

			ds_meta_uri = ds_content_uri + '/aic:content/fcr:metadata'

			# Set source datastream properties
			prop_tuples = [
				(ns_collection['rdfs'].label, Literal(self.uid + '_' + in_dsname)),
			]

			self.lconn.update_node_properties(ds_meta_uri, insert_props=prop_tuples)


	def create_or_update_instance(
			self, parent_uri, name, ref=None, file_name=None, ds=None, path=None, mimetype='application/octet-stream'
			):
		'''Creates or updates an instance.
		@TODO
		'''
		
		rdf_type = ns_collection['aic'].Master\
				if name == 'master' \
				else \
				ns_collection['aic'].Instance
		#rdf_type = 'aic:Master'\
		#		if name == 'master' \
		#		else \
		#		'aic:Instance'

		rel_name = 'has_master' \
			if name == 'master' \
			else \
			'has_instance'

		uri = parent_uri + '/aic:ds_' + name
		inst_uri = self.lconn.create_or_update_node(
			uri = uri,
			props = self._build_prop_tuples(
				insert_props = {'type' :  [rdf_type]},
				delete_props = {},
				init_insert_tuples = []
				#(self.props['type'], self._build_rdf_object(rdf_type, 'uri'))
			)['tuples'][1]
		)
		cherrypy.log('Created instance: {}'.format(inst_uri))

		# Create content datastream.
		if not file_name:
			file_name = '{}_{}{}'.format(
				os.path.basename(inst_uri), name, self._guess_file_ext(mimetype)
			)
		
		if ref:
			inst_content_uri = self.lconn.create_or_update_ref_datastream(
					uri = inst_uri + '/aic:content', ref = ref
					)
		else:
			inst_content_uri = self.lconn.create_or_update_datastream(
					uri = inst_uri + '/aic:content',
					file_name = file_name, ds = ds, path = path, mimetype = mimetype
					)

		# Add relationship in parent node.
		self.lconn.update_node_properties(
			uri = parent_uri,
			insert_props = self._build_prop_tuples(
				insert_props = {rel_name : [inst_uri]},
				delete_props = {},
				init_insert_tuples = []
			)['tuples'][1]
		)

		return inst_uri


	def _update_node(self, uri, tuples):
		'''Updates a node inserting and deleting related nodes if necessary.'''

		delete_nodes, insert_nodes = tuples['nodes']
		delete_tuples, insert_tuples, where_tuples = tuples['tuples']

		for node_type in delete_nodes.keys():
			for uri in delete_nodes[node_type]:
				self.lconn.delete_node(uri)

		for node_type in insert_nodes.keys():
			if node_type == 'comments':
				comment_uris = []
				for comment_props in insert_nodes[node_type]:
					comment_uri = self.lconn.create_or_update_node(
						uri = '{}/aic:annotations/{}'.format(uri, uuid.uuid4()),
						props = [
							(
								self._build_rdf_object(ns_collection['rdf'].type, 'uri'),
								self._build_rdf_object(ns_collection['aic'] + 'Comment', 'uri')
							),
							(
								self._build_rdf_object(ns_collection['aic'].content, 'uri'),
								self._build_rdf_object(comment_props['content'], 'literal')
							),
							(
								self._build_rdf_object(ns_collection['aic'].category, 'uri'),
								self._build_rdf_object(comment_props['category'], 'literal')
							),
						]

					)
					insert_tuples.append((
						self._build_rdf_object(*self.props['comment']),
						self._build_rdf_object(comment_uri, 'uri')
					))
					
		self.lconn.update_node_properties(
			uri,
			delete_props=delete_tuples,
			insert_props=insert_tuples,
			where_props=where_tuples
		)



