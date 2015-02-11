import cherrypy
import requests
import uuid

from rdflib import URIRef, Literal, XSD

from sspad.config.datasources import lake_rest_api
from sspad.models.sspad_model import SspadModel
from sspad.resources.rdf_lexicon import ns_collection as nsc


class TagCat(SspadModel):
    '''Tag Category model class.

    Tag categories are ordered lists containing laketype:Tag nodes in LAKE.

    @package sspad.models
    '''


    @property
    def node_type(self):
        '''@sa SspadModel::node_type'''

        return nsc['laketype'].TagCat



    @property
    def cont_uri(self):
        '''URI of container node where all tags should be stored.

        @return string
        '''

        return lake_rest_api['base_url'] + '/support/tags'



    @property
    def ns_props(self):
        '''@sa SspadModel::props'''

        return super().ns_props + (
            ('skos:prefLabel', 'literal', XSD.string),
        )



    def get_uri(self, label):
        '''Return the URI of a category by label.

        @param label (string) Category label.

        @return (string) Category URI.
        '''

        props = [
            (nsc['rdf'].type, nsc['laketype'].TagCat),
            (nsc['skos'].prefLabel, Literal(label, datatype=XSD.string)),
        ]

        return self.tsconn.get_node_uri_by_props(props)


    def list(self):
        '''Lists all categories and their labels.

        @return (list) List of all category URIs.
        '''

        q = '''
        SELECT ?cat ?label WHERE {{
            ?cat a <{}> .
            ?cat <{}> ?label .
        }}
        '''.format(
            self.node_type,
            nsc['skos'].prefLabel,
        )
        res = self.tsconn.query(q)
        #cherrypy.log('Res: {}'.format(res))

        return res


    def assert_exists(self, label):
        '''Checks if a tag category with a given label exists.'''

        props = [
            (nsc['rdf'].type, nsc['laketype'].TagCat),
            (nsc['skos'].prefLabel, Literal(label, datatype=XSD.string)),
        ]
        return True \
                if self.tsconn.get_node_uri_by_props(props) \
                else False


    def create(self, label):
        '''Create a tag category with a given label.

        @param label (string) Category label.

        @return (string) New category URI.
        '''

        if self.assert_exists(label):
            raise cherrypy.HTTPError('409 Conflict',
                    'Category with label \'{}\' exist already.'.format(label))
        else:
            uri = self.lconn.create_or_update_node(
                uri = '{}/{}'.format(self.cont_uri, uuid.uuid4()),
                props = self._build_prop_tuples(
                    insert_props = {
                        nsc['rdf'].type :  [self.node_type],
                        nsc['skos'].prefLabel : [label],

                    },
                    delete_props = {},
                    init_insert_tuples = []
                )
            )

            return uri



