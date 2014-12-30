import mimetypes

import cherrypy

from rdflib import URIRef, XSD

from sspad.models.sspad_model import SspadModel
from sspad.models.comment import Comment
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr

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
        return ns_collection['aic'].Resource



    @property
    def prop_req_names(self):
        return super().prop_req_names + (
            'label',
            'title',
            'comment', # For insert: Dict: {'cat' : <String>, 'content' : <String>} - For delete: String (comment URI)
        )



    @property
    def prop_lake_names(self):
        return super().prop_lake_names + (
            (ns_collection['dc'].title, 'literal', XSD.string),
            (ns_collection['aic'].label, 'literal', XSD.string),
            (ns_collection['aic'].hasComment, 'uri'),
        )



    @property
    def mixins(self):
        '''Mix-ins considered for updating.

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
                comment_uri = Comment().create(self.temp_uri, comment_props['content'], comment_props['category'])
                prop_list.append((self._build_rdf_object(*self.props['comment']), URIRef(comment_uri)))

        return prop_list
