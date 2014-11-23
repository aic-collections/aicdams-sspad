import cherrypy
import requests
import xml.etree.ElementTree as ET

from itertools import chain
from os.path import basename
from rdflib import Graph, URIRef, Literal, Variable
from rdflib.plugins.sparql.processor import prepareQuery
from urllib.parse import quote, unquote

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
	def __init__(self):
		auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.headers = {'Authorization': auth_str}


	def query(self, q, action='select'):
		'''Sends a SPARQL query and returns the results.'''

		cherrypy.log('Querying tstore: {}'.format(q))
		if action == 'ask':
			accept = 'text/boolean'
		elif action == 'construct':
			accept = 'application/rdf+xml'
		else: # select
			accept = 'application/sparql-results+xml'

		res = requests.get(
			self.conf['base_url'], 
			headers = dict(chain(self.headers.items(),
				[(
					'Accept',
					'{}, */*;q=0.5'.format(accept)
				)]
			)),
			params = {'query': q}
		)
		#cherrypy.log('Requesting URL: ' + res.url)
		#cherrypy.log('Query response: ' + str(res.text))
		res.raise_for_status()

		if action == 'ask':
			return res.text
		else:
			ret = []
			root = ET.fromstring(res.text)
			for result in root.find('{http://www.w3.org/2005/sparql-results#}results'):
				row = {}
				for binding in result:
					row[binding.attrib['name']] = binding[0].text
				cherrypy.log('Query result row: {}.'.format(row))
				ret.append(row)
			return ret


	def assert_node_exists_by_prop(self, prop, value):
		''' Finds if a node exists with a given literal property. '''

		q = 'ASK {{ ?r <{}> "{}"^^<http://www.w3.org/2001/XMLSchema#string> . }}'.format(prop, value)

		return True if self.query(q, 'ask') == 'true' else False


	def get_node_uri_by_prop(self, prop, value, type='string'):
		''' Get the URI of a node by a given literal property.
		
		@param prop (string) The property name as a fully qualified URI.
		@param value (string) The property value.
		@param type (string) Data type according to http://www.w3.org/2001/XMLSchema

		@return string
		'''

		q = 'SELECT ?u WHERE {{ ?u <{}> "{}"^^<http://www.w3.org/2001/XMLSchema#string> . }} LIMIT 1'.format(prop, value)

		res = self.query(q)

		cherrypy.log('get node by prop response: {} '.format(res))
		return res[0]['u'] if res else False


	def get_node_uri_by_props(self, props):
		''' Get the URI of a node by a set of literal properties.
			Properties are logically connected by AND.

			@param props (list) Property map: list of 2-tuples with URIRef of Literals for predicate and object to query for.
		@return string
		'''

		#where_graph = Graph()
		where_str = ''
		for prop in props:
			cherrypy.log('Prop: {}'.format(prop))
			where_str += '?u {} {} .\n'.format(
				prop[0].n3(),
				prop[1].n3()
			)

		q = 'SELECT ?u WHERE {{\n{} }} LIMIT 1'.format(where_str)

		res = self.query(q)

		cherrypy.log('get node by props response: {} '.format(res))
		return res[0]['u'] if res else False


