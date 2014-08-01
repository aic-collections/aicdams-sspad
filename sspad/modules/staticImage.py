import io, json

import cherrypy
from rdflib import Graph, URIRef, Literal, Variable
from wand import image

from sspad.config.datasources import fedora_rest_api
from sspad.config.datasources import datagrinder_rest_api
from sspad.modules.resource import Resource
from sspad.resources.rdf_lexicon import ns_collection

## Static Image class.
#
#  This class runs and manages Image actions.
class StaticImage(Resource):

	exposed = True


	## @sa Resource#pfx
	pfx = 'SI'

	## @sa Resource#node_type
	node_type=ns_collection['aic'].image


	## GET method.
	#
	#  Lists all images or shows properties for an image with given uid.
	#
	#  @param uid (string) UID of image to display.
	#
	#  @TODO stub
	def GET(self, uid=None, legacy_uid=None):
		
		self._setConnection()

		if uid:
			return {'message': '*stub* This is image #{}.'.format(uid)}
		elif legacy_uid:
			if self.tsconn.assertImageExistsByLegacyUid(legacy_uid):
				return {'message': '*stub* This is image with legacy UID #{}.'.format(legacy_uid)}
			else:
				raise cherrypy.HTTPError(
					'404 Not Found',
					'An image with this legacy UID does not exist.'
				)
		else:
			return {'message': '*stub* This is a list of images.'}


	## POST method.
	#
	#  Create a new image node with automatic UID by providing data and node properties.
	#
	#  @param mid			(string) Mid-prefix.
	#  @param properties	(dict) Properties to be associated with new node.
	#  @param **dstreams	(BytesIO) Arbitrary datastream(s). Name of the parameter is the datastream name.\
	#  Only the 'source' datastream is mandatory.
	#
	#  @return (dict) Message with new node information.
	def POST(self, mid, properties='{}', overwrite=False, **dstreams):
		
		self._setConnection()

		# Raise error if source is not uploaded.
		if 'source' not in dstreams.keys():
			raise cherrypy.HTTPError('400 Bad Request', 'Required source datastream missing.')

		#cherrypy.request.body.processors['multipart'] = cherrypy._cpreqbody.process_multipart
		#cherrypy.log('Max. upload size: ' + str(cherrypy.server.max_request_body_size))
		#self._setConnection()

		props = json.loads(properties)
		for p in props:
			# Wrap string props in one-element lists
			if not props[p].__class__.__name__ == 'list':
				props[p] = [props[p]]

		# Before anything else, check that if a legacy_uid parameter is
		# provied, no other image exists with that legacy UID. In the case one exists, 
		# the function shall return a '409 Conflict'.
		# The function assumes that multiple legacy UIDs can be assigned.
		if overwrite == False and 'legacy_uid' in props:
			for uid in props['legacy_uid']:
				if self.tsconn.assertImageExistsByLegacyUid(uid):
					raise cherrypy.HTTPError(
						'409 Conflict',
						'An image with the same legacy UID already exists. Not creating a new one.'
					)
		
		# Create a new UID
		uid = self.mintUid(mid)

		if 'master' not in dstreams:
			# Generate master if not present
			cherrypy.log('Master file not provided.')
			dstreams['master'] = self._generateMasterFile(dstreams['source'].file, uid + '_master.jpg')
		else:
			cherrypy.log('Master file provided.')

		# First validate all datastreams
		dsmeta = {}
		for dsname in dstreams.keys():
			ds = dstreams[dsname]
			cherrypy.log(dsname + ' class name: ' + ds.__class__.__name__)

			# If ds is a byte stream instead of a Part instance, wrap it in an
			# anonymous object as a 'file' property
			if ds.__class__.__name__ == 'bytes':
				dsObj = lambda:0 # Kind of a hack, but it works.
				dsObj.file = io.BytesIO(ds)
				dstreams[dsname] = dsObj
			elif ds.__class__.__name__ == 'BytesIO':
				dsObj = lambda:0 # Kind of a hack, but it works.
				dsObj.file = ds
				dstreams[dsname] = dsObj
			ds = dstreams[dsname]

			try:
				dsmeta[dsname] = self._validateDStream(ds.file, dsname)
			except Exception:
				raise cherrypy.HTTPError('415 Unsupported Media Type', 'Validation for datastream {} failed.'.format(dsname))
			cherrypy.log('Validation for ' + dsname + ': ' + str(dsmeta[dsname]))

		# Open Fedora transaction
		tx_uri = self.openTransaction()

		try:
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

			# Loop over all datastreams and ingest them
			for dsname in dstreams.keys():
				ds = dstreams[dsname]
				#cherrypy.log('Ingestion round: ' + dsname + ' class name: ' + ds.__class__.__name__)
				ds.file.seek(0)
				ds_content_uri = self.fconn.createOrUpdateDStream(
					img_tx_uri + '/aic:ds_' + dsname,
					ds=ds.file,
					dsname = uid + '_' + dsname + self._guessFileExt(dsmeta[dsname]['mimetype']),
					mimetype = dsmeta[dsname]['mimetype']
				)

				ds_uri = ds_content_uri.replace('/fcr:content', '')

				# Set source datastream properties
				prop_tuples = [
							(self.ns_rdf.type, self.ns_indexing.indexable),
							(self.ns_dc.title, Literal(uid + '_' + dsname)),
						]
				if dsname == 'master':
					prop_tuples.append((self.ns_rdf.type, self.ns_aicmix.imageDerivable))
				self.fconn.updateNodeProperties(ds_uri, insert_props=prop_tuples)
		except:
			# Roll back transaction if something goes wrong
			self.fconn.rollbackTransaction(tx_uri)
			raise

		# Commit transaction
		self.fconn.commitTransaction(tx_uri)

		cherrypy.response.status = 201
		cherrypy.response.headers['Location'] = img_uri

		return {"message": "Image created.", "data": {"location": img_uri}}


	## PUT method.
	#
	#  Adds or replaces datastreams or replaces the whole property set of an image.
	#
	#  @param uid		(string) Image UID.
	#  @param properties	(dict) Properties to be associated with new node.
	#  @param **dstreams	(BytesIO) Arbitrary datastream(s). Name of the parameter is the datastream name.
	#  Only the 'source' datastream is mandatory.
	#
	#  @return (dict) Message with node information.
	#
	#  @TODO Replacing property set is not supported yet, and might not be needed anyway.
	def PUT(self, uid, properties={}, **dstreams):

		self._setConnection()

		img_uri = fedora_rest_api['base_url'] + 'resources/SI/' + uid

		dsnames = sorted(dstreams.keys())
		for dsname in dsnames:
			ds = dstreams[dsname]
			src_format, src_size, src_mimetype = self._validateDStream(ds.file)

			#cherrypy.log('UID: ' + uid + '; dsname: ' + dsname + ' mimetype: ' + src_mimetype)
			#cherrypy.log('mimetype guess: ' + self._guessFileExt(src_mimetype))
			#ds.file.seek(0)
			with ds.file as file:
				src_data = file.read()
				cherrypy.log('File in ctxmgr is closed: ' + str(file.closed))
				content_uri = self.fconn.createOrUpdateDStream(
					img_uri + '/aic:ds_' + dsname,
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
					content_uri = self.fconn.createOrUpdateDStream(
						img_uri + '/aic:ds_master',
						ds=master.read(), 
						dsname = uid + '_master.jpg',
						mimetype = 'image/jpeg'
					)
				src_data = None # Flush datastream

		return {"message": "Image updated.", "data": {"location": img_uri}}

		
	## PATCH method.
	#
	#  Adds or removes properties and mixins in an image.
	#
	#  @param uid				(string) Image UID.
	#  @param insert_properties	(dict) Properties to be inserted. See FedoraConnector#createOrUpdateDStream
	#  @param delete_properties	(dict) Properties to be deleted. See FedoraConnector#createOrUpdateDStream
	#
	#  @TODO Figure out how to pass parameters in HTTP body instead of as URL params.
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
		url = fedora_rest_api['base_url'] + 'resources/SI/' + uid

		# Open Fedora transaction
		tx_uri = self.openTransaction()

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
								self.fconn.updateNodeProperties(
									url,
									delete_props=[(lake_name[0], self._rdfObject(value, lake_name[1]))],
									where_props=[(lake_name[0], self._rdfObject(value, lake_name[1]))]
								)
							else:
								delete_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))
					elif delete_props[req_name] == '':
						# Delete the whole property
						delete_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
						where_tuples.append((lake_name[0], self._rdfObject('?' + req_name, 'variable')))
				if req_name in insert_props:
					for value in insert_props[req_name]:
						insert_tuples.append((lake_name[0], self._rdfObject(value, lake_name[1])))

			#print('INSERT:',insert_tuples, 'DELETE:', delete_tuples)

			self.fconn.updateNodeProperties(
				url,
				delete_props=delete_tuples,
				insert_props=insert_tuples,
				where_props=where_tuples
			)
		except:
			self.fconn.rollbackTransaction(tx_uri)
			raise

		self.fconn.commitTransaction(tx_uri)

		cherrypy.response.status = 204
		cherrypy.response.headers['Location'] = url

		return {"message": "Image updated."}

		
	## Generate a master datastream from a source image file.
	#
	#  @param file (StringIO) Input file.
	#  @param fname (string) downloaded file name.
	def _generateMasterFile(self, file, fname):

		return self.dgconn.resizeImageFromData(file, fname, 4096, 4096)


	## Checks that the input file is a valid image.
	#
	#  @TODO more rules. So far only 'mimetype' is supported.
	def _validateDStream(self, ds, dsname='', rules={}):

		ds.seek(0)
		cherrypy.log('Validating ds: ' + dsname + ' of type: ' + str(ds))
		with image.Image(file=ds) as img:
			format = img.format
			mimetype = img.mimetype
			size = img.size
			cherrypy.log(' Image format: ' + format + ' MIME type: ' + mimetype + ' size: ' + str(size))

		ds.seek(0)

		if 'mimetype' in rules:
			if mimetype != rules['mimetype']:
				raise TypeError('MIME type of uploaded image does not match the expected one.')
		return {'format': format, 'size': size, 'mimetype': mimetype}


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
		#cherrypy.log('Value: ' + str(value))
		if type == 'literal':
			return Literal(value)
		elif type == 'uri':
			ns, tname = value.split(':')
			if ns not in ns_collection or value not in self.mixins:
				cherrypy.HTTPError('400 Bad Request', 'Relationship {} cannot be added or removed with this method.'.format(value))
			return URIRef(ns_collection[ns] + tname)
		elif type == 'variable':
			return Variable(value)
