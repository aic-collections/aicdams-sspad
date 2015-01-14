import cherrypy
import requests

from rdflib import URIRef, Literal

from sspad.models.sspad_model import SspadModel
from sspad.models.tag_cat import TagCat
from sspad.resources.rdf_lexicon import ns_collection as nsc


class Tag(SspadModel):
    '''Tag model class.

    This defines tags stored in LAKE.

    @package sspad.models
    '''


    @property
    def node_type(self):
        '''@sa SspadModel::node_type'''

        return nsc['laketype'].Tag



    @property
    def props(self):
        '''@sa SspadModel::props'''

        return super().props + (
            (nsc['aic'].category, 'uri'),
        )



    def list(self, cat_label=None):
        '''Lists all tags, optionally narrowing down the selection to a category.

        @param cat_label (string, optional) Category label. If empty (default),
            a list of all tags is returned. Otherwise, a list of all tags for the
            category bearing that label is returned.

        @return (list) List of dicts containing tag URI, label and category URI.
        '''

        cat_cond = '''
        ?cat <{}> ?cl .
        FILTER(STR(?cl="{}")) .
        '''.format(nsc['aic'].label, cat_label) \
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
            nsc['aic'].label,
            nsc['fcrepo'].hasParent,
            nsc['aiclist'].TagCat, cat_cond
        )
        res = self.tsconn.query(q)
        cherrypy.log('Res: {}'.format(res))

        return res


    def get_uri(self, label, cat_uri):
        '''Gets tag URI by a given label.

        @param cat_uri (string) Category URI.
        @param label (string) Tag label.

        @return (string) Tag URI.
        '''

        props = [
            (
                self._build_rdf_object(*self.props['label']),
                Literal(label, datatype=XSD.string),
            ),
            (
                self._build_rdf_object(self.props['type']),
                URIRef(self.node_type),
            ),
            (
                self._build_rdf_object(self.props['category']),
                URIRef(cat_uri),
            ),
        ]

        return self.tsconn.get_node_uri_by_props(props)


    def create(self, cat_label, label):
        '''Creates a new tag within a category and with a given label.

        @param cat_label (string) Category label.
        @param label (string) Tag label.

        @return (string) Tag URI.
        '''

        cat_uri = TagCat().get_uri(cat_label)
        if not cat_uri:
            raise cherrypy.HTTPError(
                '404 Not Found',
                'Tag category with label \'{}\' does not exist. Cannot create tag.'\
                        .format(cat_label)
            )
        if self.get_uri(label, cat_uri):
            raise cherrypy.HTTPError(
                '409 Conflict',
                'A tag with label \'{}\' exists in category \'{}\' already.'.\
                        format(label, cat_label)
            )
        else:
            tag_uri = self.lconn.create_or_update_node(
                parent = cat_uri,
                props = self._build_prop_tuples(
                    insert_props = {
                        nsc['rdf'].type :  [self.node_type],
                        nsc['skos'].prefLabel : [label],
                        nsc['aic'].category : [cat_uri],

                    },
                    delete_props = {},
                    init_insert_tuples = []
                )
            )

        return tag_uri


