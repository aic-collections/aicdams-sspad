import json, mimetypes

import cherrypy
from rdflib import Graph, URIRef, Literal
from wand import image

from edu.artic.sspad.connectors.datagrinder_connector import DatagrinderConnector
from edu.artic.sspad.connectors.fedora_connector import FedoraConnector
from edu.artic.sspad.connectors.uidminter_connector import UidminterConnector
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


	def GET(self, uid=None):
		'''Lists all images or shows properties for an image with given uid.
		@TODO stub
		'''
		if uid:
			return {'message': 'This is image #{}'.format(uid)}
		else:
			return {'message': 'This is a list of images.'}


	def POST(self, mid, source, master=None, meta='{}'):

		'''Create a new image node with automatic UID by providing data and node properties.'''
		
		#cherrypy.request.body.processors['multipart'] = cherrypy._cpreqbody.process_multipart

		# Set connectors - @TODO move this in __init__ method of super class
		# when you figure out how to access cherrypy.request.headers there
		self.auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.fconn = FedoraConnector(self.auth_str)
		self.dgconn = DatagrinderConnector(self.auth_str)


		meta_obj = json.loads(meta)
		
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
		AIC, AICMIX, DC, RDF =\
			ns_collection['aic'],\
			ns_collection['aicmix'],\
			ns_collection['dc'],\
			ns_collection['rdf']
		props = [
			(RDF.type, AIC.image),
			(RDF.type, AIC.citi),
			(DC.title, Literal(uid)),
			(AIC.uid, Literal(uid)),
		]

		if 'legacy_uid' in meta_obj:
			props.append((AIC.legacyUid, Literal(meta_obj['legacy_uid'])))
		if 'citi_pkey' in meta_obj:
			props.append((AIC.citiObjUid, Literal(meta_obj['citi_pkey'])))
		if 'accession_number' in meta_obj:
			props.append((AIC.citiObjAccNo, Literal(meta_obj['accession_number'])))

		self.fconn.updateNodeProperties(img_tx_uri, props)

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
		props = [(DC.title, Literal(uid + '_source'))]
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
		props = [
			(RDF.type, AICMIX.imageDerivable),
			(DC.title, Literal(uid + '_master')),
		]
		self.fconn.updateNodeProperties(master_uri, props)

		# Commit transaction
		self.fconn.commitTransaction(tx_uri)

		cherrypy.response.headers['Status'] = 201
		cherrypy.response.headers['Location'] = img_uri

		return {"message": "Image created"}


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
