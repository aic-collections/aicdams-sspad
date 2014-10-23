import mimetypes
import io
import json
import uuid

import cherrypy
import requests

from rdflib import Literal

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


	## Base properties to assign to this node type.
	@property
	def base_prop_tuples(self):
		return [
			(ns_collection['rdf'].type, self.node_type),
		]


	## Properties as specified in requests.
	#
	#  These map to #prop_lake_names.
	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'legacy_uid',
			'batch_uid',
			'tag',
			'comment',
			#'has_ext_content',
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
		)


	@property
	def mixins(self):
		return super().mixins + (
			'aicmix:derivable',
			'aicmix:overlaid',
			'aicmix:publ_web',
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
			if self.tsconn.assertAssetExistsByLegacyUid(legacy_uid):
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
				if self.tsconn.assertAssetExistsByLegacyUid(uid):
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
		tx_uri = self.lconn.openTransaction()
		#cherrypy.log('Created TX: {}'.format(tx_uri))

		try:
			# Create Asset node in tx
			res_tx_uri, res_uri = self.createNodeInTx(uid, tx_uri)

			# Set node properties
			prop_tuples = self.base_prop_tuples + [
				(ns_collection['dc'].title, Literal(uid)),
				(ns_collection['aic'].uid, Literal(uid)),
			]

			#cherrypy.log('Props available: {}'.format(list(prop_tuples)))
			for req_name, lake_name in self.props:
				if req_name in props:
					for value in props[req_name]:
						prop_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

			#cherrypy.log('Props:' + str(prop_tuples))

			self.lconn.updateNodeProperties(res_tx_uri, insert_props=prop_tuples)

			# Loop over all datastreams and ingest them
			for dsname in dstreams.keys():

				if dsname[:4] == 'ref_':
					# Create a reference node.
					in_dsname = dsname [4:]
					cherrypy.log('Creating a reference ds with name: aic:ds_{}'.format(in_dsname))
					ds_content_uri = self.lconn.createOrUpdateRefDStream(
						res_tx_uri + '/aic:ds_' + in_dsname,
						dstreams[dsname]
					)
				else:
					in_dsname = dsname
					cherrypy.log('Ingestion round (' + in_dsname + '): class name: ' + ds.__class__.__name__)
					# Create an actual datastream.
					ds = self._getIOStreamFromReq(dstreams[dsname])
					ds.seek(0)
					ds_content_uri = self.lconn.createOrUpdateDStream(
						res_tx_uri + '/aic:ds_' + dsname,
						ds = ds,
						dsname = uid + '_' + in_dsname + self._guessFileExt(dsmeta[dsname]['mimetype']),
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
			self.lconn.rollbackTransaction(tx_uri)
			raise

		# Commit transaction
		self.lconn.commitTransaction(tx_uri)

		cherrypy.response.status = 201
		cherrypy.response.headers['Location'] = res_uri

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
	def PUT(self, uid, properties={}, **dstreams):

		self._setConnection()

		res_uri = lake_rest_api['base_url'] + self.path + uid

		dsnames = sorted(dstreams.keys())
		for dsname in dsnames:
			ds = _getIOStreamFromReq(dstreams[dsname])
			src_format, src_size, src_mimetype = self._validateDStream(ds)

			#cherrypy.log('UID: ' + uid + '; dsname: ' + dsname + ' mimetype: ' + src_mimetype)
			#cherrypy.log('mimetype guess: ' + self._guessFileExt(src_mimetype))
			#ds.seek(0)
			with ds.read() as src_data:
				content_uri = self.lconn.createOrUpdateDStream(
					res_uri + '/aic:ds_' + dsname,
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
						res_uri + '/aic:ds_master',
						ds=master.read(),
						dsname = uid + '_master' + self._guessFileExt(self.master_mimetype),
						mimetype = self.master_mimetype
					)
				src_data = None # Flush datastream

		return {"message": "Resource updated.", "data": {"location": res_uri}}


	## PATCH method.
	#
	#  Adds or removes properties and mixins in an Asset.
	#
	#  @param uid				(string) Asset UID.
	#  @param insert_properties	(dict) Properties to be inserted. See LakeConnector#createOrUpdateDStream
	#  @param delete_properties	(dict) Properties to be deleted. See LakeConnector#createOrUpdateDStream
	def PATCH(self, uid, insert_properties='{}', delete_properties='{}'):

		self._setConnection()

		try:
			insert_props = json.loads(insert_properties)
			delete_props = json.loads(delete_properties)
		except:
			raise cherrypy.HTTPError(
				'400 Bad Request',
				'Properties are invalid. Please review your request.'
			)

		#cherrypy.log('Insert props:' + str(insert_props))
		#cherrypy.log('Delete props:' + str(delete_props))

		insert_tuples, delete_tuples, where_tuples = ([],[],[])

		# Open Fedora transaction
		tx_uri = self.lconn.openTransaction()
		url = '{}/{}{}'.format(tx_uri, self.path, uid)

		# Collect properties
		try:
			for req_name, lake_name in zip(self.prop_req_names, self.prop_lake_names):
				#cherrypy.log("Req. name: " + str(req_name) + "; LAKE name: " + str(lake_name))
				if req_name in delete_props:
					if isinstance(delete_props[req_name], list):
						# Delete one or more values from property
						for value in delete_props[req_name]:
							if req_name == 'type':
								# If we are removing rdf:type properties,
								# remove them one by one separately from other properties
								self.lconn.updateNodeProperties(
									url,
									delete_props=[(lake_name[0], self._rdfObject(value, lake_name[1]))],
									where_props=[(lake_name[0], self._rdfObject(value, lake_name[1]))]
								)
							elif req_name == 'tag':
								value = lake_rest_api['tags_base_url'] + value
							elif req_name == 'comment':
								pass # Handle comments in a second round
							else:
								delete_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))
					elif delete_props[req_name] == '':
						# Delete the whole property
						delete_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
						where_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
				if req_name in insert_props:
					for value in insert_props[req_name]:
						if req_name == 'tag':
							value = lake_rest_api['tags_base_url'] + value

						insert_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

			# Update node
			self.lconn.updateNodeProperties(
				url,
				delete_props=delete_tuples,
				insert_props=insert_tuples,
				where_props=where_tuples
			)

			# Add comment nodes
			if 'comment' in insert_properties and insert_properties['comment']:
				self._insert_comments(url, insert_properties['comment'])
		except:
			self.lconn.rollbackTransaction(tx_uri)
			raise

		self.lconn.commitTransaction(tx_uri)

		cherrypy.response.status = 204
		cherrypy.response.headers['Location'] = url

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


	## Adds one or more comments.
	#
	#  @param parent (string) Parent node URI (excluding (aic:annotations)
	#  @param comments (list) Comment contents. Author and creation date will be added
	#  by Fedora from request headers and timestamp.
	def _insert_comments(self, parent, comments):
		for comment in comments:
			comment_uri = self.lconn.createOrUpdateNode(
				url + '/aic:annotations/' + uuid.uuid4(),
				props = {'content' : comment}
			)

			self.lconn.updateNodeProperties(
				parent,
				insert_tuples = (
					(self.props['comment'][0], self._rdfObject(comment_uri, 'uri'))
				)
			)
