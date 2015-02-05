import mimetypes

import cherrypy

from rdflib import URIRef, XSD

from sspad.models.sspad_model import SspadModel
from sspad.models.comment import Comment
from sspad.resources.rdf_lexicon import ns_collection as nsc, ns_mgr

class Resource(SspadModel):
    '''Resource class.

    Resources are all nodes in LAKE that can have metadata. They include two
    main categories: holders and assets.
    '''

    @property
    def pfx(self):
        '''Resource prefix.

        This is used in the node UID and designates the resource type.
        It is mandatory to define it for each resource type.

        @return string

        @TODO Call uidminter and generate a (cached) map of pfx to Resource subclass names.
        '''

        return ''



    @property
    def node_type(self):
        '''@sa SspadModel::node_type'''

        return nsc['laketype'].Resource



    @property
    def ns_props(self):
        '''@sa SspadModel::props'''

        return super().ns_props + (
            ('dc:title', 'literal', XSD.string),
            ('skos:prefLabel', 'literal', XSD.string),
            #('aic:hasComment' 'uri'),
            #('aic:hasTag' 'uri'),
        )



    @property
    def mixins(self):
        '''Types (mixins) available for updating.

        @return tuple
        '''
        return (
            'aicmix:Citi',
            'aicmix:CitiPrivate',
        )



    def __init__(self):
        '''Class constructor.

        Sets up several connections and MIME types.

        @return None
        '''
        super().__init__()
        if not mimetypes.inited:
            mimetypes.init()
            for mt, ext, strict in self._add_mimetypes:
                mimetypes.add_type(mt, ext, strict)



    def _validate_datastream(self, ds, dsname='', rules={}):
        '''Validate a datastream.

        Override this method for each Node subclass.
        '''

        pass


    def _insert_nodes_in_tuples(self, type, props):
        '''@sa SspadModel::_insert_nodes_in_tuples()'''

        prop_list = []
        if type == 'comments':
            ## Create comment nodes.
            for comment_props in props:
                cherrypy.log('Inserting comment in props: {}'.format(comment_props))
                comment_uri = Comment().create(
                    self.temp_uri,
                    comment_props['aic:content'],
                    comment_props['aic:category']
                )
                prop_list.append((nsc['aic'].hasComment, URIRef(comment_uri)))

        return prop_list
