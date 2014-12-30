import uuid

import cherrypy
import requests

from rdflib import URIRef, Literal, XSD

from sspad.models.annotation import Annotation
from sspad.resources.rdf_lexicon import ns_collection


class Comment(Annotation):
    '''Comment class.

    This is a specific type of Annotation which has an additional category name.

    @package sspad.models
    @author Stefano Cossu <scossu@artic.edu>
    @date 12/11/2014
    '''

    @property
    def node_type(self):
        return ns_collection['aic'].Comment



    @property
    def default_cat(self):
        '''Default category name for unspecified comments.

        @return string
        '''

        return 'General'



    @property
    def prop_req_names(self):
        return super().prop_req_names + (
            'category', # String @TODO URI
        )



    @property
    def prop_lake_names(self):
        return super().prop_lake_names + (
            (ns_collection['aic'].category, 'literal', XSD.string),
        )



    #@property
    #def reqprops_to_rels(self):
    #   return {
    #   }



    def list(self, subject, cat=None):
        '''Lists all comments for the given subject URI.

        @param uri (string) Subject URI.
        @param cat (string, optional) Category name. If specified,
            only comments of the given category will be returned.

        @return list List of comment dicts.
        '''

        pass



    def create(self, subject_uri, content, cat=None):
        '''Create a comment.

        @sa CommentCtrl::POST()

        @return (dict) Message with new comment node information.
        '''

        # Avoiding circular reference
        from sspad.models.resource import Resource

        if not cat:
            cat = self.default_cat

        req_uri = '{}/{}/{}'.format(
            subject_uri, self.cont_name, uuid.uuid4()
        )

        comment_uri = self.connectors['lconn'].create_or_update_node(
            uri = req_uri,
            props = self._build_prop_tuples(
                insert_props = {
                    'content' : [content],
                    'category' : [cat],

                },
                delete_props = {},
                init_insert_tuples = self.base_prop_tuples
            )
        )

        # Add relationship to comment.
        self.connectors['lconn'].update_node_properties(
            subject_uri,
            insert_props=[(
                self._build_rdf_object(*Resource().props['comment']),
                URIRef(comment_uri)
            )],
        )

        return comment_uri
