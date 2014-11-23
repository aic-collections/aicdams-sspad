import cherrypy
import requests

from rdflib import URIRef, Literal

from sspad.config.datasources import lake_rest_api, datagrinder_rest_api
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.modules.node import Node
from sspad.modules.tagCat import TagCat
from sspad.resources.rdf_lexicon import ns_collection


class Tag(Node):


	exposed = True

	node_type = ns_collection['aiclist'].Tag


	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'category',
		)


	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['aic'].category, 'uri'),
		)



	## HTTP-EXPOSED METHODS ##

	def GET(self, cat_label=None, label=None):
		'''Get a tag or list of tags.'''

		self._set_connection()

		if label:
			return self.get_uri(label, cat_label)
		else:
			return self.list(cat_label)


	def POST(self, cat, label):
		self._set_connection()

		return self.create(cat, label)



	## NON EXPOSED METHODS ##

	def list(self, cat_label=None):
		'''Lists all tags, optionally narrowing down the selection to a category.'''

		cat_cond = '''
		?cat <{}> ?cl .
		FILTER(STR(?cl="{}")) .
		'''.format(ns_collection['aic'].label, cat_label) \
				if cat_label \
				else ''

		q = '''
		SELECT ?uri ?label ?cat WHERE {{
			?uri a <{}> . 
			?uri <{}> ?label . 
			?uri <{}> ?cat .
			?cat a <{}> .
			{} }}
		'''.format(
			self.node_type,
			ns_collection['aic'].label, 
			ns_collection['fcrepo'].hasParent,
			ns_collection['aiclist'].TagCat, cat_cond
		)
		res = cherrypy.request.app.config['connectors']['tsconn'].query(q)
		cherrypy.log('Res: {}'.format(res))

		return res

	
	def get_uri(self, label, cat=None):
		props = [
			(ns_collection['aic'].label, Literal(label, datatype=XSD.string)),
			(ns_collection['rdf'].type, ns_collection['aic'].Tag),
		]
		if cat:
		   props.append((ns_collection['aic'].category, cat))
		
		return cherrypy.request.app.config['connectors']['tsconn'].get_node_uri_by_props(props)


	def create(self, cat_label, label):
		'''Create a tag under an existing category.'''

		cat = TagCat()
		if not cat.assert_exists(cat_label):
			raise cherrypy.HTTPError(
				'404 Not Found', 'Category with label \'{}\' does not exist.'.format(cat_label)
			)
		else:
			if self.assert_tag_exists(cat, label):
				raise cherrypy.HTTPError(
					'409 Conflict',
					'A tag with label \'{}\' exists in category \'{}\' already.'.\
							format(label, cat)
				)
			else:
				tag_uri = cherrypy.request.app.config['connectors']['lconn'].\
						create_or_update_node(
					props = self._build_prop_tuples(
						insert_props = {
							'type' :  [self.node_type],
							'label' : [label],

						},
						delete_props = {},
						init_insert_tuples = []
					)['tuples'][1]
				)

				return tag_uri


	def create(self, cat_label, label):
		'''Creates a new tag within a category and with a given label.'''

		cat = TagCat()
		cat_uri = cat.get_uri(cat_label)
		if not cat_uri:
			raise cherrypy.HTTPError(
				'404 Not Found',
				'Tag category with label \'{}\' does not exist. Cannot create tag.'\
						.format(cat_label)
			)
		tag_uri = cherrypy.request.app.config['connectors']['lconn'].\
				create_or_update_node(
			parent = cat_uri,
			props = self._build_prop_tuples(
				insert_props = {
					'type' :  [self.node_type],
					'label' : [label],
					'category' : [cat_uri],

				},
				delete_props = {},
				init_insert_tuples = []
			)['tuples'][1]
		)

		return tag_uri


