import mimetypes
import io
import json
import os

import cherrypy
import requests

from rdflib import URIRef, Literal

from sspad.config.datasources import lake_rest_api
from sspad.connectors.uidminter_connector import UidminterConnector
from sspad.models.resource import Resource
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr


class Asset(Resource):
	'''Asset class.

	This is the base class for all Assets.
	'''

	@property
	def node_type(self):
		return ns_collection['aic'].Asset



	@property
	def master_mimetype(self):
		'''MIME type used for master generation.

		@return string

		@TODO Use another method to map MIME types to various generated datastreams.
		'''

		return 'image/jpeg'


	default_comment_type = 'general'



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



	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['aic'].legacyUid, 'literal', 'string'),
			(ns_collection['aic'].batchUid, 'literal', 'string'),
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



	@property
	def reqprops_to_rels(self):
		return {
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



	@property
	def path(self):
		'''Path between the repo root and the asset node.

		@return string
		'''

		pfx = self.pfx + '/' if self.pfx else ''
		return 'resources/assets/' + pfx



	## HTTP-EXPOSED METHODS ##

	def GET(self, uid=None, legacy_uid=None):
		'''GET method.

		Lists all Assets or shows properties for an asset with given uid.

		@param uid (string) UID of Asset to display.

		@return string

		@TODO stub
		'''

		self._set_connection()

		if uid:
			return {'message': '*stub* This is Asset #{}.'.format(uid)}
		elif legacy_uid:
			if self.connectors['tsconn'].assert_node_exists_by_prop(ns_collection['aic'] + 'legacyUid', legacy_uid):
				return {'message': '*stub* This is Asset with legacy UID #{}.'.format(legacy_uid)}
			else:
				raise cherrypy.HTTPError(
					'404 Not Found',
					'An asset with this legacy UID does not exist.'
				)
		else:
			return {'message': '*stub* This is a list of Assets.'}



	def POST(self, mid, props='{}', **dstreams):
		'''POST method.

		Create a new Asset node with automatic UID by providing data and node properties.

		@param mid			(string) Mid-prefix.
		@param props	(dict) Properties to be associated with new node.
		@param **dstreams	(BytesIO) Arbitrary datastream(s).
			Name of the parameter is the datastream name.
			If the datastream is to be ingested directly into LAKE, the variable value is the actual data.
			If the datastream is in an external URL and must be a reference,
			the variable name is prefixed with ref_ and the value is a URL (e.g. 'ref_source' will ingest a reference ds called 'source').
			Only the 'source' datastream is mandatory (or 'ref_source' if it is a reference).

		@return (dict) Message with new node information.
		'''

		cherrypy.log('\n')
		cherrypy.log('************************')
		cherrypy.log('Begin ingestion process.')
		cherrypy.log('************************')
		cherrypy.log('')

		self._set_connection()

		props_dict = json.loads(props)

		return self.create(mid, props_dict, **dstreams)



	def PUT(self, uid=None, uri=None, props='{}', **dstreams):
		'''PUT method.

		Adds or replaces datastreams or replaces the whole property set of an Asset.

		@param uid		(string) Asset UID. Specify this or 'uri' only if the node is known to exist,
		   otherwise a 404 Not Found will be thrown.
		@param uri		(string) Asset URI. If this is not provided, node will be searched by UID.
		@param props	(dict) Properties to be associated with new or updated node.
		   The 'legacy_uid' property is searched for conflicts or to find nodes when neither 'uri' or 'uid' are known.
		@param **dstreams	(BytesIO) Arbitrary datastream(s). Name of the parameter is the datastream name.
		Only the 'source' datastream is mandatory. @sa POST

		@return (dict) Message with node information.

		@TODO Replacing property set is not supported yet, and might not be needed anyway.
		'''

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



	def PATCH(self, uid=None, uri=None, insert_props='{}', delete_props='{}'):
		'''PATCH method.

		Adds or removes properties and mixins in an Asset.

		@param uid				(string) Asset UID.
		@param insert_props	(dict) Properties to be inserted.
		@param delete_props	(dict) Properties to be deleted.

		@return (dict) Message with new node information.
		'''

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
		self.tx_uri = self.connectors['lconn'].open_transaction()
		self.uri_in_tx = self.uri.replace(lake_rest_api['base_url'], tx_uri + '/')

		# Collect properties
		try:
			self._update_node(
				self.uri_in_tx,
				props = {
					'insert_props' : insert_props,
					'delete_props' : delete_props,
					'init_insert_tuples' : [],
				}
			)
		except:
			self.connectors['lconn'].rollbackTransaction(self.tx_uri)
			raise

		self.connectors['lconn'].commitTransaction(self.tx_uri)

		cherrypy.response.status = 204
		cherrypy.response.headers['Location'] = self.uri # @TODO Actually verify the URI from response headers.

		return {"message": "Asset updated."}



	## NON-EXPOSED METHODS ##

	def create(self, mid, props={}, **dstreams):
		'''Create an asset. @sa POST

		@return (dict) Message with new asset node information.
		'''

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
				if self.connectors['tsconn'].assert_node_exists_by_prop(ns_collection['aic'] + 'legacyUid', uid):
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
		self.tx_uri = self.connectors['lconn'].open_transaction()
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
			cherrypy.log('Asset create init tuples: {}'.format(init_tuples))

			cherrypy.log('Asset create properties: {}'.format(props))
			self._update_node(
				self.uri_in_tx,
				props = {
					'insert_props' : props,
					'init_insert_tuples' : init_tuples
				}
			)

			# Loop over all datastreams and ingest them
			self._ingest_instances(dstreams, dsmeta)

		except:
			# Roll back transaction if something goes wrong
			#self.connectors['lconn'].rollbackTransaction(self.tx_uri)
			raise

		# Commit transaction
		self.connectors['lconn'].commitTransaction(self.tx_uri)

		cherrypy.response.status = 201
		cherrypy.response.headers['Location'] = self.uri

		return {"message": "Asset created.", "data": {"location": self.uri}}



	def update(self, uid=None, uri=None, props='{}', **dstreams):
		'''Updates an asset. @sa PUT

		@return (dict) Message with updated asset node information.
		'''

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



	def mint_uid(self, mid=None):
		'''Calls an eternal service to generate and returns a UID.

		@param mid (string) Second prefix needed for certain types.

		@return (string) Generated UID.
		'''

		try:
			self.uid = UidminterConnector().mint_uid(self.pfx, mid)
		except:
			raise RuntimeError('Could not generate UID.')
		return self.uid



	def _set_uri(self, uri=None, uid=None, legacy_uid=None):
		'''Validates the existence of a node from provided URI, UID or legacy UID
		and set #uri to a value according to the first valid one found.
		At leaast one of uri, uid or legacy_uid values must be provided.

		@param uri (string, optional) URI of node, if known.
		@param uid (string, optional) AIC UID of Asset, if known.
		@param legacy_uid (string, optional) Legacy UID of Asset, if known.

		@return (bool) Whether the class-level member #uri was set.
		'''

		if not uri and not uid and not legacy_uid:
			raise ValueError('No valid identifier provided.')

		self.uri = None

		# First check the URI.
		if uri:
			if self.connectors['lconn'].assert_node_exists(uri):
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

		check_uri = self.connectors['tsconn'].get_node_uri_by_prop(check_prop, check_uid)

		if check_uri:
			self.uri = check_uri
			return True
		else:
			return False



	def _check_uid_dupes(self, uid=None, legacy_uid=None):
		'''Checks if a node with a given UID or a given legacy UID exists.
		At least one of uid or legacy_uid must be provided.

		@param uid (string, optional) UID of node to check duplicates for.
		@param legacy_uid (string, optional) Legacy UID of node to check duplicates for.

		@return (boolean) Whether a duplicate has been found.
		@throws (HTTPError) 409 Conflict if a duplicate exists.

		@TODO Only return boolean and let caller method raise exceptions if appropriate.
		'''

		if not uid and not legacy_uid:
			raise ValueError('Neither uid or legacy_uid were provided. Cannot check for duplicates.')

		if uid:
			uri_uid = self.connectors['tsconn'].find_node_uri_by_prop(ns_collection['aic'] + 'uid', uid)
			if not self.uri == uri_uid:
				cherrypy.response.headers['link'] = uri_uid
				raise cherrypy.HTTPError('409 Conflict', 'A node with UID {} exsists already.'.format(uri))
		if legacy_uid:
			uri_legacy_uid = self.connectors['tsconn'].find_node_uri_by_prop(ns_collection['aic'] + 'legacyUid', legacy_uid)
			if not self.uri == uri_legacy_uid:
				cherrypy.response.headers['link'] = legacy_uri_uid
				raise cherrypy.HTTPError('409 Conflict', 'A node with legacy UID {} exsists already.'.format(legacy_uri))

		return True



	def _generate_master(self, dstreams):
		'''Generates master datastream from source if missing and returns the complete list of datastreams.

		@param dstreams (dict) Dict of datastreams where keys are datastream names and values are datastreams.

		@return (dict) Updated list of datastreams.
		'''

		if 'master' not in dstreams.keys() and 'ref_master' not in dstreams.keys():
			# Generate master if not present
			cherrypy.log('Master file not provided.')
			if 'ref_source' in dstreams.keys():
				cherrypy.log('Requesting {}...'.format(dstreams['ref_source']))
				ds_binary = self.connectors['lconn'].get_binary_stream(dstreams['ref_source'])

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
		'''Ensures that provided datastreams are valid and conform to a set of conditions.
		This methiod is overridden for each asset type.

		@param dstreams (dict) Dict of datastreams. Keys are dataastream names and values are datastreams.

		@return (dict) Datastream metadata coming from validators.
		'''

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



	def _get_iostream_from_req(self, ds):
		'''Normalize the behaviour of a datastream object regardless of its source.

		If ds is a byte stream instead of a Part instance, wrap it in an
		anonymous object as a 'file' property.

		@param ds The BytesIO or bytes object to be normalized.

		@return (BytesIO)
		'''

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



	def _ingest_instances(self, dstreams, dsmeta):
		'''Loops over datastreams and ingests them by calling #create_or_update_instance() iteratively within a transaction.

		@param dstreams (dict) Dict of datastreams. Keys are datastream names and values are datastreams.
		@param dsmeta (dict) Dict of datastream metadata. Keys are datastream names and values are dicts of property names and values.

		@return (boolean) True
		'''

		cherrypy.log('DSmeta: {}'.format(dsmeta))
		for dsname in dstreams.keys():

			if dsname[:4] == 'ref_':
				# Create a reference node.
				in_dsname = dsname [4:]
				cherrypy.log('Creating a reference ds with name: aic:ds_{}'.format(in_dsname))
				inst_uri = self.create_or_update_instance(
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
				inst_uri = self.create_or_update_instance(
					parent_uri = self.uri_in_tx,
					name = in_dsname,
					ds = ds,
					mimetype = dsmeta[dsname]['mimetype']
				)



	def create_or_update_instance(
			self, parent_uri, name, ref=None, file_name=None, ds=None, path=None, mimetype='application/octet-stream'
			):
		'''Creates or updates an instance.

		@param parent_uri (string) URI of the container Asset node for the instance.
		@param name (string) Name of the datastream, e.g. 'master' or 'source'.
		@param ref (string, optional) Reference URI for remote source.
		@param file_name (string, optional) File name for the downloaded datastream. If empty, this is built from the asset UID and instance name (default).
		@param ds (BytesIO, optional) Raw datastream.
		@param path (string, optional) Reference path for source file in current filesystem.
		@param mimetype (string, optional) MIME type of provided datastream. Default is 'application/octet-stream'.

		@return (string) New instance URI.
		'''

		rdf_type = ns_collection['aic'].Master\
				if name == 'master' \
				else \
				ns_collection['aic'].Instance

		rel_name = 'has_master' \
			if name == 'master' \
			else \
			'has_instance'

		uri = parent_uri + '/aic:ds_' + name
		inst_uri = self.connectors['lconn'].create_or_update_node(
			uri = parent_uri + '/aic:ds_' + name,
			props = self._build_prop_tuples(
				insert_props = {
					'type' :  [rdf_type],
					'label' : [self.uid + '_' + name],
				},
				init_insert_tuples = []
			)
		)
		cherrypy.log('Created instance: {}'.format(inst_uri))

		# Create content datastream.
		if not file_name:
			file_name = '{}_{}{}'.format(
				os.path.basename(inst_uri), name, self._guess_file_ext(mimetype)
			)

		if ref:
			inst_content_uri = self.connectors['lconn'].create_or_update_ref_datastream(
					uri = inst_uri + '/aic:content', ref = ref
					)
		else:
			inst_content_uri = self.connectors['lconn'].create_or_update_datastream(
					uri = inst_uri + '/aic:content',
					file_name = file_name, ds = ds, path = path, mimetype = mimetype
					)


		# Add relationship in parent node.
		self._update_node(
			uri = parent_uri,
			props = {
				'insert_props' : {rel_name : [inst_uri]},
				'init_insert_tuples' : [],
			}
		)

		return inst_uri



