import rdflib
from rdflib import Graph
from rdflib.namespace import Namespace, NamespaceManager

from sspad.config.datasources import lake_rest_api

ns_collection = {
    'aic':
        Namespace('http://definitions.artic.edu/ontology/1.0/'),
    'aicdb':
        Namespace('http://definitions.artic.edu/ontology/1.0/dbconn/'),
    'aiclist':
        Namespace('http://definitions.artic.edu/ontology/1.0/auth_list/'),
    'aicmeta':
        Namespace('http://definitions.artic.edu/ontology/1.0/metadata/'),
    'aicmix':
        Namespace('http://definitions.artic.edu/ontology/1.0/mixin/'),
    'authz':
        Namespace('http://fedora.info/definitions/v4/authorization#'),
    'cidoc':
        Namespace('http://www.cidoc-crm.org/cidoc-crm/'),
    'dc':
        rdflib.namespace.DC,
    'edm':
        Namespace('http://www.europeana.eu/schemas/edm/'),
    'exif':
        Namespace('http://www.w3.org/2003/12/exif/ns#'),
    'fcrepo':
        Namespace('http://fedora.info/definitions/v4/repository#'),
    'fedora':
        Namespace('http://fedora.info/definitions/v4/rest-api#'),
    'fedoraconfig':
        Namespace('http://fedora.info/definitions/v4/config#'),
    'fedorarelsext':
        Namespace('http://fedora.info/definitions/v4/rels-ext#'),
    'foaf':
        rdflib.namespace.FOAF,
    'image':
        Namespace('http://www.modeshape.org/images/1.0'),
    'indexing':
        Namespace('http://fedora.info/definitions/v4/indexing#'),
    'lake':
        Namespace('http://definitions.artic.edu/lake/1.0/'),
    'lakeschema':
        Namespace('http://definitions.artic.edu/lake/1.0/schema/'),
    'laketype':
        Namespace('http://definitions.artic.edu/lake/1.0/node_type/'),
    'ldp':
        Namespace('http://www.w3.org/ns/ldp#'),
    'mix':
        Namespace('http://www.jcp.org/jcr/mix/1.0'),
    'mode':
        Namespace('http://www.modeshape.org/1.0'),
    'nt':
        Namespace('http://www.jcp.org/jcr/nt/1.0'),
    'premis':
        Namespace('http://www.loc.gov/premis/rdf/v1#'),
    'ore':
        Namespace('http://www.openarchives.org/ore/terms/'),
    'rdf':
        rdflib.namespace.RDF,
    'rdfs':
        rdflib.namespace.RDFS,
    'skos':
        rdflib.namespace.SKOS,
    'sv':
        Namespace('http://www.jcp.org/jcr/sv/1.0'),
    'test':
        Namespace('info:fedora/test/'),
    'xml':
        Namespace('http://www.w3.org/XML/1998/namespace'),
    'xmlns':
        Namespace('http://www.w3.org/2000/xmlns/'),
    'xs':
        Namespace('http://www.w3.org/2001/XMLSchema'),
    'xsd':
        rdflib.namespace.XSD,
    'xsi':
        Namespace('http://www.w3.org/2001/XMLSchema-instance'),
}

# Warning: some possible duplicate values in ns_collection will be overwritten in this dict.
# So this is not a 1:1 reverse mapping to ns_collection.
pfx_collection = {ns_collection[k] : k for k in ns_collection.keys()}

ns_mgr = NamespaceManager(Graph())
ns_pfx_sparql = dict()

for ns,uri in ns_collection.items():
    ns_mgr.bind(ns, uri, override=False)
    ns_pfx_sparql[ns] = 'PREFIX {}: <{}>'.format(ns, uri)

