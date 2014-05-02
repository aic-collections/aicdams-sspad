import json, mimetypes

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
	"""Static Image class.

	This class runs and manages Image actions.
	@TODO Make subclass of new 'Node' class and move related methods there.
	"""
	exposed = True


	pfx = 'SI'

	NS_AIC, NS_AICMIX, NS_DC, NS_RDF =\
		ns_collection['aic'],\
		ns_collection['aicmix'],\
		ns_collection['dc'],\
		ns_collection['rdf']

	prop_lake_names = (
		NS_RDF.type,
		NS_AIC.legacyUid,
		NS_AIC.citiObjUid,
		NS_AIC.citiObjAccNo,
		NS_AIC.citiAgentUid,
		NS_AIC.citiPlaceUid,
		NS_AIC.citiExhibUid,
		NS_AIC.citiImgDBankUid,
	)

	prop_req_names = (
		'type',
		'legacy_uid',
		'citi_obj_pkey',
		'citi_obj_acc_no',
		'citi_agent_pkey',
		'citi_place_pkey',
		'citi_exhib_pkey',
		'citi_imgdbank_pkey',
	)

	NS_AIC.exposed = False
	NS_AICMIX.exposed = False
	NS_DC.exposed = False
	NS_RDF.exposed = False


	def GET(self, uid=None):
		'''Lists all images or shows properties for an image with given uid.
		@TODO stub
		'''
		if uid:
			return {'message': 'This is image #{}'.format(uid)}
		else:
			return {'message': 'This is a list of images.'}


	def POST(self, mid, source, master=None, properties='{}'):

		'''Create a new image node with automatic UID by providing data and node properties.'''
		
		#cherrypy.request.body.processors['multipart'] = cherrypy._cpreqbody.process_multipart

		# Set connectors - @TODO move this in __init__ method of super class
		# when you figure out how to access cherrypy.request.headers there
		self.auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.fconn = FedoraConnector(self.auth_str)
		self.dgconn = DatagrinderConnector(self.auth_str)


		props = json.loads(properties)

		# @TODO Before anything else, check that if a legacy_uid parameter is
		# provied, no other image exists with that legacy UID. In the case one exists, 
		# the function shall return a '409 Conflict'.
		
		# Create a new UID
		uid = self.mintUid(mid)

		# Validate source
		src_format, src_size, src_mimetype = self._validateDStream(source.file)

		if master == None:
			# Generate master if not present
			master = self._generateMasterFile(source.file, uid + '_master.jpg')

		else:
			# Validate master
			self._validateDStream(master, {'mimetype': 'image/jpeg'})


		# Open Fedora transaction
		tx_uri = self.openTransaction()

		# Create image node in tx
		img_tx_uri, img_uri = self.createNodeInTx(uid, tx_uri)

		# Set node properties
		prop_tuples = [
			(self.NS_RDF.type, self.NS_AIC.image),
			(self.NS_RDF.type, self.NS_AIC.citi),
			(self.NS_DC.title, Literal(uid)),
			(self.NS_AIC.uid, Literal(uid)),
		]

		for req_name, lake_name in zip(self.prop_req_names, self.prop_lake_names):
			if req_name in props:
				for value in props[req_name]:
					prop_tuples.append((lake_name, Literal(value)))

		print('Props:', prop_tuples)

		self.fconn.updateNodeProperties(img_tx_uri, prop_tuples)

		# Upload source datastream
		#print('Source dstream:', source.file)
		source.file.seek(0)
		source_content_uri = self.fconn.createOrUpdateDStream(
			img_tx_uri + '/aic:ds_source',
			ds=source.file, 
			dsname = uid + '_source' + mimetypes.guess_extension(src_mimetype),
			mimetype = src_mimetype
		)

		source_uri = source_content_uri.replace('/fcr:content', '')

		# Set source datastream properties
		props = [(self.NS_DC.title, Literal(uid + '_source'))]
		self.fconn.updateNodeProperties(source_uri, props)

		# Upload master datastream
		print('Master dstream:', master)
		master_content_uri = self.fconn.createOrUpdateDStream(
			img_tx_uri + '/aic:ds_master',
			ds=master,
			dsname = uid + '_master.jpg',
			mimetype = 'image/jpeg'
		)

		master_uri = master_content_uri.replace('/fcr:content', '')

		# Set master datastream properties
		prop_tuples = [
			(self.NS_RDF.type, self.NS_AICMIX.imageDerivable),
			(self.NS_DC.title, Literal(uid + '_master')),
		]
		self.fconn.updateNodeProperties(master_uri, prop_tuples)

		# Commit transaction
		self.fconn.commitTransaction(tx_uri)

		cherrypy.response.headers['Status'] = 201
		cherrypy.response.headers['Location'] = img_uri

		return {"message": "Image created"}


	def PUT(self, uid, meta={}, **kwargs):
		''' Update datastreams or property set of an image.
		NOTE: The sent property set will replace the existing one completely.
		'''

		pass

		
	#@cherrypy.config(**{'tools.json_in.force': True})
	def PATCH(self, uid, insert_properties='{}', delete_properties='{}'):
		''' Add or removes properties and mixins in an image. '''

		#print('Req parameters:', cherrypy.request.params)
		self.auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.fconn = FedoraConnector(self.auth_str)

		insert_props = json.loads(insert_properties)
		delete_props = json.loads(delete_properties)

		#print('Add props:',insert_props)

		insert_tuples, delete_tuples, where_tuples = ([],[],[])
		for req_name, lake_name in zip(self.prop_req_names, self.prop_lake_names):
			if req_name in delete_props:
				if isinstance(delete_props[req_name], list):
					# Delete one or more values from property
					for value in delete_props[req_name]:
						delete_tuples.append((lake_name, Literal(value)))
				elif isinstance(delete_props[req_name], str):
					# Delete the whole property
					delete_tuples.append((lake_name, Variable('?v')))
					where_tuples.append((lake_name, Variable('?v')))
			if req_name in insert_props:
				for value in insert_props[req_name]:
					insert_tuples.append((lake_name, Literal(value)))

		#print('INSERT:',insert_tuples, 'DELETE:', delete_tuples)

		url = fedora_rest_api['base_url'] + 'resources/SI/' + uid
		self.fconn.updateNodeProperties(url, delete_tuples, insert_tuples, where_tuples)

		cherrypy.response.headers['Status'] = 204
		cherrypy.response.headers['Location'] = url

		
	def _generateMasterFile(self, file, fname):
		'''Generate a master datastream from a source image file.'''

		return self.dgconn.resizeImageFromData(file, fname, 2048, 2048)


	def _validateDStream(self, ds, rules={}):
		'''Checks that the input file is a valid image.
		@TODO more rules
		'''

		#print('ds: ', ds)
		with image.Image(file=ds) as img:
			format = img.format
			mimetype = img.mimetype
			size = img.size
			print('Image format:', format, 'MIME type:', mimetype, 'size:', size)

		ds.seek(0)

		if 'mimetype' in rules:
			if mimetype != rules['mimetype']:
				return false
		return (format, size, mimetype)
