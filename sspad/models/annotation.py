import uuid

import cherrypy
import requests

from rdflib import URIRef, Literal, XSD

from sspad.models.sspad_model import SspadModel
from sspad.resources.rdf_lexicon import ns_collection as nsc


class Annotation(SspadModel):
    '''Annotation class.

    This is the base class for all Annotations, which includes Comments, Captions, etc.

        @package sspad.models
        @author Stefano Cossu <scossu@artic.edu>
        @date 12/11/2014
    '''

    @property
    def node_type(self):
        '''@sa SspadModel::node_type'''

        return nsc['laketype'].Annotation



    @property
    def cont_name(self):
        '''Container node name for all annotations under a node.

        All annotations are assumed to have a 1-to-1 relationship with a
        Resource (called the subject). They are stored in containers
        under the related subject node. The full Annotation path is therefore:
        <subject URI>/<value of this variable>/<annotation ID>

        @return string
        '''

        return 'aic:annotations'



    @property
    def ns_props(self):
        '''@sa SspadModel::props'''

        return super().ns_props + (
            ('aic:content', 'literal', XSD.string),
        )



    def list(self, subject):
        '''Lists all annotations for the given subject URI.

        @sa AnnotationCtrl::GET()
        '''

        pass



    def create(self, subject_uri, content):
        '''Create an Annotation.

        @sa AnnotationCtrl::POST()
        '''

        uri = '{}/{}/{}'.format(
            subject_uri, self.cont_name, uuid.uuid4()
        )

        ann_uri = self.lconn.\
                create_or_update_node(
            uri = uri,
            props = self._build_prop_tuples(
                insert_props = {
                    'content' : [content],
                },
                delete_props = {},
                init_insert_tuples = self.base_prop_tuples
            )
        )

        return ann_uri
