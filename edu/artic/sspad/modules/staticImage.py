import json, shutil

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
		if uid:
			return {'message': 'This is image #{}'.format(uid)}
		else:
			return {'message': 'This is a list of images.'}


	def PUT(self, mid, source, master=None, meta='{}'):
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
		format, size = self.validateDStream(source.file)

		if master == None:
			# Generate master if not present
			master = self.generateMasterFile(source.file, uid + '_master.jpg')

		else:
			# Validate master
			self.validateDStream(master, {'mimeType': 'jpeg'})


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
		
		#print(img_uri)


		# Upload source datastream
		#print('Source dstream:', source.__dict__)
		source_uri = self.fconn.createOrUpdateDStream(
			img_tx_uri + '/aic:ds_source', ds=source.file
		)

		# Set source datastream properties
		props = [(DC.title, Literal(uid + '_source'))]
		self.fconn.updateNodeProperties(source_uri, props)

		# Upload master datastream
		source.file.seek(0)
		master_uri = self.fconn.createOrUpdateDStream(
			img_tx_uri + '/aic:ds_master', ds=master.file #@TODO Switch file
		)

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


	def generateMasterFile(self, file, fname):
		''' @TODO '''
		return self.dgconn.resizeImageFromData(file, fname, 200, 200)


	def validateDStream(self, ds, rules={}):
		''' @TODO rules '''
		#print('ds: ', ds)
		with image.Image(file=ds) as img:
			format = img.format
			size = img.size
			print('Image metadata:', img.__dict__)
		ds.seek(0)
		return (format, size)
