import cherrypy
import requests

from rdflib import URIRef, Literal

from sspad.config.datasources import lake_rest_api, datagrinder_rest_api
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.modules.node import Node
from sspad.resources.rdf_lexicon import ns_collection


class Tag(Node):


	exposed = True

	node_type = ns_collection['aiclist'].Tag


	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'label',
			#'category'
		)


	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['rdfs'].label, 'literal'),
			#(ns_collection['aic'].category, 'uri'),
		)



	## HTTP-EXPOSED METHODS ##

	def GET(self, cat=None, label=None):
		'''Get a tag or list of tags.'''

		self._set_connection()

		if label:
			return self.get_tag_uri(label, cat)
		else:
			return self.get_tags(cat)


	def POST(self, cat, label):
		return self.create(label)



	## NON EXPOSED METHODS ##

	def get_tags(self, cat=None):
		cat_cond = '?cat <{}> "{}"^^<http://www.w3.org/2001/XMLSchema#string> .'.format(
			ns_collection['rdfs'].label, cat
		) \
				if cat \
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
			ns_collection['rdfs'].label, 
			ns_collection['fcrepo'].hasParent,
			ns_collection['aiclist'].TagCat, cat_cond
		)
		res = self.tsconn.query(q)
		cherrypy.log('Res: {}'.format(res))

		return res

	
	def get_tag_uri(self, label, cat=None):
		props = [
			{
				'name' : ns_collection['rdfs'].label,
				'value' : label,
			},
			{
				'name' : ns_collection['rdf'].type,
				'value' : ns_collection['aic'].Tag,
			},
		]
		if cat:
		   props.append((ns_collection['aic'].category, cat))
		
		return tsconn.get_node_uri_by_props(props)


	def assert_cat_exists(self, label):
		'''Checks if a tag category with a given label exists.'''

		return True \
				if self.tsconn.get_node_uri_by_props([
					{
						'name' : ns_collection['rdf'] + 'type',
						'value' : ns_collection['aiclist'] + 'TagCat',
						'type' : 'uri'
					},
					{
						'name' : ns_collection['rdfs'] + 'label',
						'value' : label
					}
				]) \
				else False


	def create(self, cat_label, label):
		if not self.assert_cat_exists(cat_label):
			raise cherrypy.HTTPError('404 Not Found', 'Category with label \'{}\' does not exist.'.format(cat_label))
		else:
			if self.assert_tag_exists(cat, label):
				raise cherrypy.HTTPError(
					'409 Conflict',
					'A tag with label \'{}\' exists in category \'{}\' already.'.format(label, cat)
				)
			else:
				tag_uri = self.lconn.create_or_update_node(
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


	def create_cat(self, label):
		cat_uri = self.lconn.create_or_update_node(
			props = self._build_prop_tuples(
				insert_props = {
					'type' :  [ns_collection['aiclist'].TagCat],
					'label' : [label],

				},
				delete_props = {},
				init_insert_tuples = []
			)['tuples'][1]
		)

		return cat_uri


	def create_tag(self, cat_label, label):
		'''Creates a new tag within a category and with a given label.'''

		tag_uri = self.lconn.create_or_update_node(
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


