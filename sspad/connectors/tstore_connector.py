from itertools import chain
import cherrypy, requests
from os.path import basename
from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql.processor import prepareQuery
from urllib.parse import quote

from sspad.config.datasources import tstore_rest_api, tstore_schema_rest_api
#from sspad.resources.rdf_lexicon import ns_mgr
from sspad.resources.rdf_lexicon import ns_collection


## TstoreConnector class.
#
# Handles operations related to the triplestore indexer and schema.
class TstoreConnector:

	## Triplestore config for indexer.
	conf = tstore_rest_api

	## Triplestore config for repo schema information.
	sconf = tstore_schema_rest_api


	## Class constructor.
	#
	# Sets authorization parameters based on incoming auth headers.
	#
	# @param auth (string) Authorization string as passed by incoming headers.
	def __init__(self, auth):
		self.headers = {'Authorization': auth}
		#cherrypy.log('Headers:', self.headers)


	def query(self, q):
		'''Sends a SPARQL query and returns the results.'''

		res = requests.get(
			self.conf['base_url'], 
			headers = dict(chain(self.headers.items(),
				[(
					'Accept',
					'text/boolean, */*;q=0.5'
				)]
			)),
			params = {'query': q}
		)
		#cherrypy.log('Requesting URL: ' + res.url)
		#cherrypy.log('h for UID: ' + str(res.text))
		res.raise_for_status()

		return res.text


	def assert_node_exists_by_prop(self, prop, value):
		''' Finds if an image exists with a given UID. '''

		q = 'ASK {{ ?r <{}> "{}"^^<http://www.w3.org/2001/XMLSchema#string> . }}'.format(prop, value)

		return True if self.query(q) == 'true' else False


	def get_node_uri_by_prop(self, prop, value):
		''' Get the URI of a node by a given property.
		
		@param prop (string) The property name as a fully qualified URI.
		@param value (string) The property value.

		@return string
		'''

		q = 'SELECT ?u WHERE {{ ?u <{}> "{}"^^<http://www.w3.org/2001/XMLSchema#string> . }} LIMIT 1'.format(prop, value)

		res = self.query(q)

		return res


