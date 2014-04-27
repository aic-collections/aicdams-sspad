import json, re

from bottle import abort, request, response, route, HTTPResponse
from rdflib import Graph, URIRef, Literal

from edu.artic.sspad.connectors.uidminter_connector import UidminterConnector
from edu.artic.sspad.connectors.fedora_connector import FedoraConnector
from edu.artic.sspad.modules.base_module import BaseModule
from edu.artic.sspad.resources.rdf_lexicon import ns_collection

class Image(BaseModule):
	"""Image module.

	This class runs and manages Image actions.
	"""

	def postMethod(self):
		"""Creates a new image node from uploaded files."""
		parms = request.forms
		files = request.files
		if 'source' in files and 'mid' in parms:
			return self.create(
				parms.get('mid'), \
				json.loads(parms.get('meta')), \
				files.source.file.read(), \
				files.master.file.read() if 'master' in files else None \
			)
		else:
			abort(400)


	def create(self, mid, meta, source, master):
		"""Create a new image node with automatic UID by providing data and node properties."""
		#print('Creating image with mid:', mid, ', meta:', meta)
		

		# Validate source
		self.validateDStream(source, {})

		if master == None:
			# Generate master if not present
			#TODO
			master = self.generateMasterFile(source)

		else:
			# Validate master
			self.validateDStream(master, {'mimeType': 'jpeg'})


		# Create a new UID
		uid = UidminterConnector().mintUid("SI", mid)

		conn = FedoraConnector()


		# Open Fedora transaction
		tx_uri = conn.openTransaction()


		# Create image node in tx
		#node = URIRef(img_uri)
		img_tx_uri = conn.createOrUpdateNode(tx_uri + '/resources/SI/' + uid)
		img_uri = re.sub(r'/tx:[^\/]+/', img_tx_uri, '/')


		# Set node properties
		AIC, AICMIX, DC, RDF = ns_collection['aic'], ns_collection['aicmix'], ns_collection['dc'], ns_collection['rdf']
		props = [\
			(RDF.type, AIC.image),\
			(RDF.type, AIC.citi),\
			(DC.title, Literal(uid)),\
			(AIC.uid, Literal(uid)),\
		]

		if meta['legacy_uid'] != None:
			props.append((AIC.legacyUid, Literal(meta['legacy_uid'])))
		if meta['citi_pkey'] != None:
			props.append((AIC.citiObjUid, Literal(meta['citi_pkey'])))
		if meta['accession_number'] != None:
			props.append((AIC.citiObjAccNo, Literal(meta['accession_number'])))

		conn.updateNodeProperties(img_tx_uri, props)
		
		print(img_uri)


		# Upload source datastream
		source_uri = conn.createOrUpdateNode(img_tx_uri + '/aic:ds_source', ds=source)


		# Set source datastream properties
		props = [(DC.title, Literal(uid + '-source'))]
		conn.updateNodeProperties(source_uri, props)


		# Upload master datastream
		source_uri = conn.createOrUpdateNode(img_tx_uri + '/aic:ds_master', ds=master)


		# Set source datastream properties
		props = [\
			(RDF.type, AICMIX.imageDerivable),\
			(DC.title, Literal(uid + '-master')),\
		]
		conn.updateNodeProperties(source_uri, props)




		# Commit transaction
		conn.commitTransaction(tx_uri)

		raise HTTPResponse(status=201, headers={'Location': img_uri})


	def generateMasterFile(self, source):
		''' @TODO '''
		pass


	def validateDStream(self, ds, rules):
		''' @TODO '''
		pass
