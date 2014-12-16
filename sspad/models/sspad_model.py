import cherrypy
import mimetypes
import re
import uuid

from abc import ABCMeta, abstractmethod
from rdflib import URIRef, Literal, Variable, XSD
from urllib.parse import urlparse

from sspad.config.datasources import lake_rest_api
from sspad.connectors.datagrinder_connector import DatagrinderConnector
from sspad.connectors.lake_connector import LakeConnector
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.resources.rdf_lexicon import ns_collection


class SspadModel(metaclass=ABCMeta):
    '''SspadModel class.

    This is the base class for all Fedora nodes.
    This class is initialized by instantiation from a controller. Therefore, its constructor
    method can refer to cherrypy request parameters.

    @package sspad.models
    '''

    @property
    def node_type(self):
        '''RDF type.

        This is a URI that reflects the node type set in the LAKE CND.

        @sa https://github.com/aic-collections/aicdams-lake/tree/master-aic/fcrepo-webapp/src/aic/resources/cnd

        @return rdflib.URIRef
        '''

        return ns_collection['fedora'].Resource



    @property
    def _add_mimetypes(self):
        '''Additional MIME types.

        They are added to the known list for guessing file extensions.

        @return tuple
        '''

        return (
            ('image/jpeg', '.jpeg', True),
            ('image/psd', '.psd', False),
            ('image/vnd.adobe.photoshop', '.psd', True),
            ('image/x-psd', '.psd', False),
        )



    @property
    def reqprops_to_rels(self):
        '''Request properties to resource prefix mapping.

        Keys are properties in prop_req_names.
        Values are prefixes assigned to the resource that the Asset should be linked to.

        @return dict
        '''

        return {}




    @property
    def prop_req_names(self):
        '''Properties as specified in requests.

        These map to #prop_lake_names.

        @return tuple
        '''

        return (
            'type',
            'label',
        )



    @property
    def prop_lake_names(self):
        '''Tuples defining properties stored in LAKE for this model.

        First tuple element is the property URI.
        Second element is a string defining property type, which can be 'literal', 'uri' or 'variable'.
        Third element is optional and only available for 'literal' data type and defines the XMLSchema data type.

        @return tuple

        @TODO Add lang option.
        '''

        return (
            (ns_collection['rdf'].type, 'uri'),
            (ns_collection['aic'].label, 'literal', XSD.string),
        )



    @property
    def props(self):
        return dict(zip(self.prop_req_names, self.prop_lake_names))



    @property
    def base_prop_tuples(self):
        '''Base properties to assign to this node type.

        @return list
        '''

        return [
            (ns_collection['rdf'].type, self.node_type),
        ]



    #@property
    #def tx_uri(self):
    #    '''Returns the current transaction URI.

    #    If no transaction is open, it opens a new one.


    #    @return string
    #    '''

    #    if not self._tx_uri:
    #        self._open_transaction()

    #    return self._tx_uri



    @property
    def temp_uri(self):
        '''Returns the current model's URI in the current transaction if a transaction
            is open; otherwise it returns the permanent model URI.

        @return string
        '''

        return self.uri_in_tx if self.uri_in_tx else self.uri



    ## GENERAL METHODS ##

    def __init__(self):
        '''Sets up connections to external services.

        Connector objects are available via the #connectors dict.
        If this method needs to be redefined in subclasses, make sure that this superclass __init__
        is called first, to make sure that connections to external services are appropriately established.

        @return None
        '''

        cherrypy.log('Setting connectors...')
        self.lconn = LakeConnector()
        self.dgconn = DatagrinderConnector()
        self.tsconn = TstoreConnector()



    ## CRUD METHODS ##

    def create_node_in_tx(self, uid):
        '''Creates a node within a transaction in LAKE.

        @param uid      (string) UID of the node to be generated.

        @return tuple Two resource URIs: one in the transaction and one outside of it.
        '''

        if not self.tx_uri:
            self._open_connection()

        self.uri_in_tx = self.lconn.create_or_update_node(
            parent='{}/{}'.format(self.tx_uri,self.path)
        )

        self.uri = self._tx_uri_to_notx_uri(self.uri_in_tx)

        return True



    def patch(self, insert_props={}, delete_props={}):
        '''Adds or removes properties and mixins in a node.

        @param uid (string) Node UID.
        @param insert_props (dict) Properties to be inserted.
        @param delete_props (dict) Properties to be deleted.

        @return (dict) Message with new node information.
        '''

        #cherrypy.log('Insert props:' + str(insert_props))
        #cherrypy.log('Delete props:' + str(delete_props))

        # Open Fedora transaction
        self.tx_uri = self.lconn.open_transaction()
        self.uri_in_tx = self.uri.replace(lake_rest_api['base_url'], self.tx_uri + '/')

        # Collect properties
        try:
            self._update_node(
                self.temp_uri,
                props = {
                    'insert_props' : insert_props,
                    'delete_props' : delete_props,
                    'init_insert_tuples' : [],
                }
            )
        except:
            self._rollback_tansaction()
            raise

        self._commit_transaction()

        return True



    ## PRIVATE METHODS ##

    def _tx_uri_to_notx_uri(self, tx_uri):
        '''Converts node URI inside transaction to URI outside of transaction.'''

        return re.sub(r'/tx:[^\/]+/', '/', tx_uri) # FIXME Ugly. Use more reliable methods.



    def _guess_file_ext(self, mimetype):
        '''Guesses file extension from MIME types.

        @param mimetype (string) MIME type, such as 'image/jpeg'

        @return (string) Extetnsion guessed (including leading period)
        '''

        ext = mimetypes.guess_extension(mimetype) or '.bin'
        cherrypy.log.error('Guessing MIME type for {}: {}'.format(mimetype, ext))
        return ext



    def _build_prop_tuples(
            self, insert_props={}, delete_props={}, init_insert_tuples=[], ignore_broken_rels=True
            ):
        '''Build delete, insert and where tuples suitable for #LakeConnector:update_node_properties
            from a list of insert and delete properties.
            Also builds a list of nodes that need to be deleted and/or inserted to satisfy references.

            @param insert_props (dict, optional) Properties to be inserted.
            @param delete_props (dict, optional) Properties to be deleted.
            @param init_insert_tuples (list, optional) Initial properties coming from default settings,
                already formatted as tuples.
            @param ignore_broken_rels (boolean, optional) If set to True (default), the application throws
                an exception if a realtionship with a CITI object is broken.
                If False, the property is skipped and the process goes forward.
                WARNING: DO NOT SET TO TRUE IN PRODUCTION ENVIRONMENT!

            @return (dict) Dict containing two elements:
                'nodes' is a tuple containing a list of nodes to be deleted and a list of nodes to be created.
                'tuples' is a tuple containing a list of tuples to be added, one of tuples to be removed,
                and one of WHERE conditions.
        '''

        cherrypy.log('Initial insert tuples: {}.'.format(init_insert_tuples))
        insert_tuples = init_insert_tuples
        delete_tuples, where_tuples = ([],[])
        insert_nodes, delete_nodes = ({},{})

        for req_name in self.props.keys():
            lake_name = self.props[req_name]

            # Delete tuples + nodes
            if req_name in delete_props:
                if isinstance(delete_props[req_name], list):
                    # Delete one or more values from property
                    for value in delete_props[req_name]:
                        if req_name == 'comment':
                            delete_nodes['comments'] = delete_props['comment']
                        delete_tuples.append((lake_name[0], self._build_rdf_object(value, lake_name[1])))

                elif delete_props[req_name] == '':
                    # Delete the whole property
                    delete_tuples.append((lake_name[0], Variable(req_name)))
                    where_tuples.append((lake_name[0], Variable(req_name)))

            # Insert tuples + nodes
            if req_name in insert_props:
                cherrypy.log('Adding req. name {} from insert_props {}...'.format(req_name, insert_props))
                #cherrypy.log('Insert props: {}'.format(insert_props.__class__.__name__))
                for value in insert_props[req_name]:
                    # Check if property is a relationship
                    if req_name in self.reqprops_to_rels:
                        rel_type = self.reqprops_to_rels[req_name]
                        ref_uri = self.tsconn.get_node_uri_by_prop(ns_collection['aicdb'] + 'citi_pkey', value)
                        if not ref_uri:
                            if ignore_broken_rels:
                                continue
                            else:
                                raise cherrypy.HTTPError(
                                    '404 Not Found',
                                    'Referenced CITI resource with CITI Pkey {} does not exist. Cannot create relationship.'.format(value)
                                )
                        value = ref_uri
                    elif req_name == 'tag':
                        insert_nodes['tags'] = insert_props['tag']
                        #value = lake_rest_api['tags_base_url'] + value
                        continue
                    elif req_name == 'comment':
                        insert_nodes['comments'] = insert_props['comment']
                        continue
                    cherrypy.log('Value for {}: {}'.format(req_name, value))
                    insert_tuples.append(
                        (lake_name[0], self._build_rdf_object(
                            value, lake_name[1], lake_name[2] if len(lake_name) > 2 else None
                        ))
                    )

        return {
            'nodes' : (delete_nodes, insert_nodes),
            'tuples' : (delete_tuples, insert_tuples, where_tuples),
        }


    def _build_rdf_object(self, value, type, datatype=None):
        '''Returns an RDF object from a value and a type.

        Depending on the value of @p type, a literal object, a URI or a variable (?var) is created.

        @param value    (string) Value to be processed.
        @oaram type     (string) One of 'literal', 'uri', 'variable'.
        @oaram datatype (string, optional) Data type for 'literal' type.

        @return (rdflib.URIRef | rdflib.Literal | rdflib.Variable) rdflib object.
        '''

        cherrypy.log('Converting value to RDF {} object: {}'.format(type, value))
        if type == 'uri':
            return URIRef(value)
        elif type == 'variable':
            return Variable(value)
        else:
            return Literal(value, datatype=datatype)


    def _update_node(self, uri, props):
        '''Updates a node inserting and deleting related nodes if necessary.

        @param uri (stirng) URI of the node to be updated.
        @param tuples (dict) Map of properties and nodes to be updated,
        to be passed to #_build_prop_tuples.

        @return None
        '''

        tuples = self._build_prop_tuples(**props)

        delete_nodes, insert_nodes = tuples['nodes']
        delete_tuples, insert_tuples, where_tuples = tuples['tuples']

        for node_type in delete_nodes.keys():
            for del_uri in delete_nodes[node_type]:
                self.lconn.delete_node(del_uri)

        for node_type in insert_nodes.keys():
            insert_tuples += self._insert_nodes_in_tuples(node_type, insert_nodes[node_type])

        self.lconn.update_node_properties(
            uri,
            delete_props=delete_tuples,
            insert_props=insert_tuples,
            where_props=where_tuples)



    def _insert_nodes_in_tuples(self, type, props):
        '''Performs additional operations for nodes to be added.

        Override this method in sub-classes.

        @param type (string) Node type name.
        @param props (list) List of dicts of properties (key: property name, value: property value)
            to be added to node. Each dict makes up a distinct node.

        @return (list) Insert tuples for the additional nodes.
        '''

        return []



    def _open_transaction(self):
        '''Opens a transaction in LAKE and sets the #tx_uri property.

        NOTE: It is advisable to use the #temp_uri instead of #uri or #tx_uri where applicable.

        @return None
        '''

        self.tx_uri = self.lconn.open_transaction()



    def _commit_transaction(self):
        '''Commits a transaction and clears transaction URI members.

        @return None
        '''

        if self.lconn.commit_transaction(self.tx_uri):
            self.tx_uri = None
            self.uri_in_tx = None




    def _rollback_transaction(self):
        '''Rolls back a transaction and clears transaction URI members.

        @return None
        '''

        if self.lconn.rollback_transaction(self.tx_uri):
            self.tx_uri = None
            self.uri_in_tx = None




