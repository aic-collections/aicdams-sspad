import uuid

import cherrypy
import requests

from rdflib import URIRef, Literal, XSD

from sspad.models.sspad_model import SspadModel
from sspad.resources.rdf_lexicon import ns_collection


class Annotation(SspadModel):
	'''Annotation class.

	This is the base class for all Annotations, which includes Comments, Captions, etc.

		@author Stefano Cossu <scossu@artic.edu>
		@date 12/11/2014
	'''

	@property
	def node_type(self):
		return ns_collection['aic'].Annotation



	@property
	def cont_name(self):
		'''Container node name for all annotations under a node.

		All annotations are assumed to have a 1-to-1 relationship with a Resource (called the subject).
			Therefore they are stored in containers under the related subject node.
			The full Annotation path is therefore: <subject URI>/<value of this variable>/<annotation ID>

		@return string
		'''

		return 'aic:annotations'



	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'content', # String
		)



	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['aic'].content, 'literal', XSD.string),
		)



	def list(self, subject):
		'''Lists all annotations for the given subject URI.

		@param uri (string) Subject URI.

		@return list List of annotation dicts.
		'''

		pass



	def create(self, subject_uri, content, cat=None):
		'''Create an Annotation.

		@sa AnnotationCtrl::POST()

		@return (dict) Message with new Annotation node information.
		'''

		if not cat:
			cat = self.default_cat

		parent_uri = '{}/{}/{}'.format(
			subject_uri, self.cont_name, uuid.uuid4()
		)

		ann_uri = cherrypy.request.app.config['connectors']['lconn'].\
				create_or_update_node(
			parent = parent_uri,
			props = self._build_prop_tuples(
				insert_props = {
					'content' : [content],
				},
				delete_props = {},
				init_insert_tuples = self.base_prop_tuples
			)
		)

		return ann_uri
