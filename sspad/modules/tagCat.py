import cherrypy
import requests

from rdflib import URIRef, Literal

from sspad.config.datasources import lake_rest_api, datagrinder_rest_api
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.modules.node import Node
from sspad.resources.rdf_lexicon import ns_collection


class TagCat(Node):


	exposed = True

	node_type = ns_collection['aiclist'].TagCat

	cont_uri = lake_rest_api['base_url'] + '/support/tags'


	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'label',
		)


	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['rdfs'].label, 'literal'),
		)



	## HTTP-EXPOSED METHODS ##

	def GET(self, label=None):
		'''Get a category URI from a label or a list of categories.'''

		self._set_connection()

		return self.get_uri(label) \
				if label \
				else self.list()


	def POST(self, label):
		'''Create a tag category with a given label.'''

		self._set_connection()

		return self.create(label)



	## NON EXPOSED METHODS ##

	def get_uri(self, label):
		'''Returns the URI of a category by label.'''

		props = [
			{
				'name' : ns_collection['rdfs'].label,
				'value' : label,
			},
			{
				'name' : ns_collection['rdf'].type,
				'value' : ns_collection['aic'].TagCat,
			},
		]
		
		return cherrypy.request.app.config['connectors']['tsconn'].get_node_uri_by_props(props)

	
	def list(self):
		'''Lists all categories and their labels.'''

		q = '''
		SELECT ?cat ?label WHERE {{
			?cat <{}>  .
			?cat a <{}> .
		}}
		'''.format(
			ns_collection['rdfs'].label, 
			ns_collection['fcrepo'].hasParent,
			self.node_type,
		)
		res = cherrypy.request.app.config['connectors']['tsconn'].query(q)
		#cherrypy.log('Res: {}'.format(res))

		return res


	def assert_exists(self, label):
		'''Checks if a tag category with a given label exists.'''

		props = [
			{
				'name' : ns_collection['rdf'].type,
				'value' : ns_collection['aiclist'].TagCat,
				'type' : 'uri'
			},
			{
				'name' : ns_collection['rdfs'].label,
				'value' : label
			}
		]
		return True \
				if cherrypy.request.app.config['connectors']['tsconn']\
						.get_node_uri_by_props(props) \
				else False


	def create(self, label):
		'''Creates a new tag category.'''
		
		if self.assert_exists(label):
			raise cherrypy.HTTPError('409 Conflict', 'Category with label \'{}\' exist already.'.format(label))
		else:
			uri = cherrypy.request.app.config['connectors']['lconn'].create_or_update_node(
				parent = self.cont_uri,
				props = self._build_prop_tuples(
					insert_props = {
						'type' :  [self.node_type],
						'label' : [label],

					},
					delete_props = {},
					init_insert_tuples = []
				)['tuples'][1]
			)

			return uri



