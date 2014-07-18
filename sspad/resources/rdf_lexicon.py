import rdflib
from rdflib import Graph
from rdflib.namespace import Namespace, NamespaceManager

ns_collection = {\
	'aic':				Namespace('http://artic.edu/definitions/ontology/1.0#'), \
	'aicmeta':			Namespace('http://artic.edu/definitions/ontology/1.0/metadata#'), \
	'aicmix':			Namespace('http://artic.edu/definitions/ontology/1.0/mixin#'), \
	'authz':			Namespace('http://fedora.info/definitions/v4/authorization#'), \
	'cidoc':			Namespace('http://www.cidoc-crm.org/cidoc-crm/'), \
	'dc':				rdflib.namespace.DC, \
	'exif':				Namespace('http://www.w3.org/2003/12/exif/ns#'), \
	'fcrepo':			Namespace('http://fedora.info/definitions/v4/repository#'), \
	'fedora':			Namespace('http://fedora.info/definitions/v4/rest-api#'), \
	'fedoraconfig':		Namespace('http://fedora.info/definitions/v4/config#'), \
	'fedorarelsext':	Namespace('http://fedora.info/definitions/v4/rels-ext#'), \
	'foaf':				rdflib.namespace.FOAF, \
	'image':			Namespace('http://www.modeshape.org/images/1.0'), \
	'indexing':			Namespace('http://fedora.info/definitions/v4/indexing#'), \
	'ldp':				Namespace('http://www.w3.org/ns/ldp#'), \
	'mix':				Namespace('http://www.jcp.org/jcr/mix/1.0'), \
	'mode':				Namespace('http://www.modeshape.org/1.0'), \
	'nt': 				Namespace('http://www.jcp.org/jcr/nt/1.0'), \
	'premis': 			Namespace('http://www.loc.gov/premis/rdf/v1#'), \
	'rdf':				rdflib.namespace.RDF, \
	'rdfs': 			rdflib.namespace.RDFS, \
	'skos': 			rdflib.namespace.SKOS, \
	'sv': 				Namespace('http://www.jcp.org/jcr/sv/1.0'), \
	'test':				Namespace('info:fedora/test/'), \
	'xml': 				Namespace('http://www.w3.org/XML/1998/namespace'), \
	'xmlns':			Namespace('http://www.w3.org/2000/xmlns/'), \
	'xs': 				Namespace('http://www.w3.org/2001/XMLSchema'), \
	'xsd': 				rdflib.namespace.XSD, \
	'xsi': 				Namespace('http://www.w3.org/2001/XMLSchema-instance'), \
}

ns_mgr = NamespaceManager(Graph())
for ns,uri in ns_collection.items():
	ns_mgr.bind(ns, uri, override=False)

