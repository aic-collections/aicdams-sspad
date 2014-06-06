from itertools import chain
import cherrypy, requests
from os.path import basename
from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql.processor import prepareQuery
from urllib.parse import quote

from edu.artic.sspad.config import host
from edu.artic.sspad.config.datasources import tstore_rest_api, tstore_schema_rest_api
#from edu.artic.sspad.resources.rdf_lexicon import ns_mgr
from edu.artic.sspad.resources.rdf_lexicon import ns_collection

class TstoreConnector:


	conf = tstore_rest_api
	sconf = tstore_schema_rest_api


	def __init__(self, auth):
		self.headers = {'Authorization': auth}
		#print('Headers:', self.headers)


	def assertImageExistsByLegacyUid(self,uid):
		''' Finds if an image exists with a given UID. '''

		query = 'ASK {{ ?r <{}> "{}"{} . }}'.format(
			ns_collection['aic'] + 'legacyUid',
			uid,
			'^^<http://www.w3.org/2001/XMLSchema#string>'
		)
		res = requests.get(
			self.conf['base_url'], 
			headers = dict(chain(self.headers.items(),
				[(
					'Accept',
					'text/boolean, */*;q=0.5'
				)]
			)),
			params = {'query': query}
		)
		#cherrypy.log.error('Requesting URL: ' + res.url)
		#cherrypy.log.error('h for UID: ' + str(res.text))
		res.raise_for_status()

		return True if res.text == 'true' else False



