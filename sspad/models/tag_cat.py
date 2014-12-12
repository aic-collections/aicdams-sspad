import cherrypy
import requests

from rdflib import URIRef, Literal, XSD

from sspad.config.datasources import lake_rest_api
from sspad.models.sspad_model import SspadModel
from sspad.resources.rdf_lexicon import ns_collection


class TagCat(SspadModel):
    '''Tag Category model class.

    Tag categories are ordered lists containing aiclist:Tag nodes in LAKE.

    @package sspad.models
    '''


    @property
    def node_type(self):
        return ns_collection['aiclist'].TagCat



    @property
    def cont_uri(self):
        '''URI of container node where all tags should be stored.

        @return string
        '''

        return lake_rest_api['base_url'] + '/support/tags'



    @property
    def prop_req_names(self):
        return super().prop_req_names + (
            'label',
        )



    @property
    def prop_lake_names(self):
        return super().prop_lake_names + (
            (ns_collection['aic'].label, 'literal', 'string'),
        )



    def get_uri(self, label):
        '''Returns the URI of a category by label.

        @param label (string) Category label.

        @return (string) Category URI.
        '''

        props = [
            (ns_collection['rdf'].type, ns_collection['aiclist'].TagCat),
            (ns_collection['aic'].label, Literal(label, datatype=XSD.string)),
        ]

        return cherrypy.request.app.config['connectors']['tsconn'].get_node_uri_by_props(props)


    def list(self):
        '''Lists all categories and their labels.

        @return (list) List of all category URIs.
        '''

        q = '''
        SELECT ?cat ?label WHERE {{
            ?cat <{}>  .
            ?cat a <{}> .
        }}
        '''.format(
            ns_collection['aic'].label,
            ns_collection['fcrepo'].hasParent,
            self.node_type,
        )
        res = cherrypy.request.app.config['connectors']['tsconn'].query(q)
        #cherrypy.log('Res: {}'.format(res))

        return res


    def assert_exists(self, label):
        '''Checks if a tag category with a given label exists.'''

        props = [
            (ns_collection['rdf'].type, ns_collection['aiclist'].TagCat),
            (ns_collection['aic'].label, Literal(label, datatype=XSD.string)),
        ]
        return True \
                if cherrypy.request.app.config['connectors']['tsconn']\
                        .get_node_uri_by_props(props) \
                else False


    def create(self, label):
        '''Create a tag category with a given label.

        @param label (string) Category label.

        @return (string) New category URI.
        '''

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
                )
            )

            return uri



