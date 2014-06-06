import io, json

import cherrypy
from rdflib import Graph, URIRef, Literal, Variable
from wand import image

from edu.artic.sspad.connectors.datagrinder_connector import DatagrinderConnector
from edu.artic.sspad.connectors.fedora_connector import FedoraConnector
from edu.artic.sspad.connectors.uidminter_connector import UidminterConnector
from edu.artic.sspad.config.datasources import fedora_rest_api
from edu.artic.sspad.config.datasources import datagrinder_rest_api
from edu.artic.sspad.modules.resource import Resource
from edu.artic.sspad.resources.rdf_lexicon import ns_collection

class StaticImage(Resource):
	'''Static Image class.

	This class runs and manages Image actions.
	@TODO Make subclass of new 'Node' class and move related methods there.
	'''
	exposed = True


	pfx = 'SI'

	ns_aic, ns_aicmix, ns_dc, ns_rdf, ns_indexing =\
		ns_collection['aic'],\
		ns_collection['aicmix'],\
		ns_collection['dc'],\
		ns_collection['rdf'],\
		ns_collection['indexing']


	''' Tuples of LAKE namespaces and data types.
		Data type string can be 'literal', 'uri' or 'variable'.
		'''
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

	mixins = [
		'aicmix:citiPrivate',
		'aicmix:derivable',
		'aicmix:overlaid',
		'aicmix:publ_web',
	]


	def GET(self, uid=None):
		'''Lists all images or shows properties for an image with given uid.
		@TODO stub
		'''
		if uid:
			return {'message': '*stub* This is image #{}'.format(uid)}
		else:
			return {'message': '*stub* This is a list of images.'}


	def POST(self, mid, properties='{}', **dstreams):

		'''Create a new image node with automatic UID by providing data and node properties.'''
		
		if 'master' not in dstreams.keys():
			raise cherrypy.HTTPError('400 Bad Request', 'Required master datastream missing.')

		#cherrypy.request.body.processors['multipart'] = cherrypy._cpreqbody.process_multipart
		#cherrypy.log('Max. upload size: ' + str(cherrypy.server.max_request_body_size))
		self._setConnection()

		props = json.loads(properties)
		for p in props:
			''' Wrap string props in one-element lists '''
			if not props[p].__class__.__name__ == 'list':
				props[p] = [props[p]]

		# Before anything else, check that if a legacy_uid parameter is
		# provied, no other image exists with that legacy UID. In the case one exists, 
		# the function shall return a '409 Conflict'.
		# The function assumes that multiple legacy UIDs can be assigned.
		if 'legacy_uid' in props:
			for uid in props['legacy_uid']:
				if self.tsconn.assertImageExistsByLegacyUid(uid):
                                    raise cherrypy.HTTPError('409 Conflict', 'An image with the same legacy UID already exists. Not creating a new one.')

		
		# Create a new UID
		uid = self.mintUid(mid)

		#print('Multipart: ', cherrypy.request.body.__dict__)
		# Validate source

		for dsname in dstreams.keys():
			ds = dstreams[dsname]
			cherrypy.log.error(dsname + ' data type: ' + ds.__class__.__name__)
			# @TODO Move all datastream ingestion operations under this loop

		# If source is a byte stream instead of a Part instance, wrap it in an
		# anonymous object as a 'file' property
		source = dstreams['source']
		if source.__class__.__name__ == 'bytes':
			sourceObj = lambda:0 # Kind of a hack, but it works.
			sourceObj.file = io.BytesIO(source)
			source = sourceObj

		src_format, src_size, src_mimetype = self._validateDStream(source.file)

		if 'master' not in dstreams:
			# Generate master if not present
			cherrypy.log.error('Master file not provided.')
			master = self._generateMasterFile(source.file, uid + '_master.jpg')

		else:
			cherrypy.log.error('Master file provided.')
			master = dstreams['master']
			if master.__class__.__name__ == 'bytes':
				masterObj = lambda:0 # Kind of a hack, but it works.
				masterObj.file = io.BytesIO(master)
				master = masterObj
			# Validate master
			self._validateDStream(master.file, {'mimetype': 'image/jpeg'})

		# Open Fedora transaction
		tx_uri = self.openTransaction()

		# Create image node in tx
		img_tx_uri, img_uri = self.createNodeInTx(uid, tx_uri)

		# Set node properties
		prop_tuples = [
			(self.ns_rdf.type, self.ns_aic.image),
			(self.ns_rdf.type, self.ns_aic.citi),
			(self.ns_dc.title, Literal(uid)),
			(self.ns_aic.uid, Literal(uid)),
		]

		for req_name, lake_name in zip(self.prop_req_names, self.prop_lake_names):
			if req_name in props:
				for value in props[req_name]:
					prop_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

		print('Props:', prop_tuples)

		self.fconn.updateNodeProperties(img_tx_uri, insert_props=prop_tuples)

		# Upload source datastream
		#print('Source dstream:', source.file)
		source.file.seek(0)
		source_content_uri = self.fconn.createOrUpdateDStream(
			img_tx_uri + '/aic:ds_source',
			ds=source.file, 
			dsname = uid + '_source' + self._guessFileExt(src_mimetype),
			mimetype = src_mimetype
		)

		source_uri = source_content_uri.replace('/fcr:content', '')

		# Set source datastream properties
		prop_tuples = [
                    (self.ns_rdf.type, self.ns_indexing.indexable),
                    (self.ns_dc.title, Literal(uid + '_source')),
                ]
		self.fconn.updateNodeProperties(source_uri, insert_props=prop_tuples)

		# Upload master datastream
		print('Master dstream:', master)
		master_content_uri = self.fconn.createOrUpdateDStream(
			img_tx_uri + '/aic:ds_master',
			ds=master.file,
			dsname = uid + '_master.jpg',
			mimetype = 'image/jpeg'
		)

		master_uri = master_content_uri.replace('/fcr:content', '')

		# Set master datastream properties
		prop_tuples = [
			(self.ns_rdf.type, self.ns_aicmix.imageDerivable),
			(self.ns_rdf.type, self.ns_indexing.indexable),
			(self.ns_dc.title, Literal(uid + '_master')),
		]
		self.fconn.updateNodeProperties(master_uri, insert_props=prop_tuples)

		# Commit transaction
		self.fconn.commitTransaction(tx_uri)

		cherrypy.response.headers['Status'] = 201
		cherrypy.response.headers['Location'] = img_uri

		return {"message": "Image created"}


	def PUT(self, uid, properties={}, **dstreams):
		''' Add or replace datastreams or replace the whole property set of an image. '''

		self._setConnection()

		img_url = fedora_rest_api['base_url'] + 'resources/SI/' + uid

		dsnames = sorted(dstreams.keys())
		for dsname in dsnames:
			ds = dstreams[dsname]
			src_format, src_size, src_mimetype = self._validateDStream(ds.file)

			#cherrypy.log.error('UID: ' + uid + '; dsname: ' + dsname + ' mimetype: ' + src_mimetype)
			#cherrypy.log.error('mimetype guess: ' + self._guessFileExt(src_mimetype))
			#ds.file.seek(0)
			with ds.file as file:
				src_data = file.read()
				cherrypy.log.error('File in ctxmgr is closed: ' + str(file.closed))
				content_uri = self.fconn.createOrUpdateDStream(
					img_url + '/aic:ds_' + dsname,
					ds=src_data,
					dsname = uid + '_' + dsname + self._guessFileExt(src_mimetype),
					mimetype = src_mimetype
				)

				if dsname == 'source' and 'master' not in dsnames:
					# Recreate master file automatically if source is provided
					# without master
					cherrypy.log.error('No master file provided with source, re-creating master.')
					cherrypy.log.error('DS: '+str(ds))
					master = self._generateMasterFile(src_data, uid + '_master.jpg')
					content_uri = self.fconn.createOrUpdateDStream(
						img_url + '/aic:ds_master',
						ds=master.read(), 
						dsname = uid + '_master.jpg',
						mimetype = 'image/jpeg'
					)
				src_data = None # Flush datastream

		return {"message": "Image updated."}

		
	def PATCH(self, uid, insert_properties='{}', delete_properties='{}'):
		''' Add or removes properties and mixins in an image.
		@TODO Figure out how to pass parameters in HTTP body instead of as URL params.
		'''

		print('Req parameters:', str(cherrypy.request.params))
		self._setConnection()

		insert_props = json.loads(insert_properties)
		delete_props = json.loads(delete_properties)

		#cherrypy.log.error('Insert props:' + str(insert_props))
		#cherrypy.log.error('Delete props:' + str(delete_props))

		insert_tuples, delete_tuples, where_tuples = ([],[],[])
		for req_name, lake_name in zip(self.prop_req_names, self.prop_lake_names):
			if req_name in delete_props:
				if isinstance(delete_props[req_name], list):
					# Delete one or more values from property
					for value in delete_props[req_name]:
						delete_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))
				elif isinstance(delete_props[req_name], str):
					# Delete the whole property
					delete_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
					where_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
			if req_name in insert_props:
				for value in insert_props[req_name]:
					insert_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

		#print('INSERT:',insert_tuples, 'DELETE:', delete_tuples)

		url = fedora_rest_api['base_url'] + 'resources/SI/' + uid
		self.fconn.updateNodeProperties(
			url,
			delete_props=delete_tuples,
			insert_props=insert_tuples,
			where_props=where_tuples
		)

		cherrypy.response.headers['Status'] = 204
		cherrypy.response.headers['Location'] = url

		return {"message": "Image updated."}

		
	def _generateMasterFile(self, file, fname):
		'''Generate a master datastream from a source image file.'''

		return self.dgconn.resizeImageFromData(file, fname, 2048, 2048)


	def _validateDStream(self, ds, rules={}):
		'''Checks that the input file is a valid image.
		@TODO more rules
		'''

		cherrypy.log.error('ds: ' + str(ds))
		with image.Image(file=ds) as img:
			format = img.format
			mimetype = img.mimetype
			size = img.size
			cherrypy.log.error(' Image format: ' + format + ' MIME type: ' + mimetype + ' size: ' + str(size))

		ds.seek(0)

		if 'mimetype' in rules:
			if mimetype != rules['mimetype']:
				return false
		return (format, size, mimetype)


	def _rdfObject(self, value, type):
		cherrypy.log.error('Value: ' + str(value))
		if type == 'literal':
			return Literal(value)
		elif type == 'uri':
			ns, tname = value.split(':')
			if ns not in ns_collection or value not in self.mixins:
				cherrypy.HTTPError('400 Bad Request', 'Relationship {} cannot be added or removed with this method.'.format(value))
			return URIRef(ns_collection[ns] + tname)
		elif type == 'variable':
			return Variable(value)
