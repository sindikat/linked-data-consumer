from rdflib import Graph, ConjunctiveGraph, Dataset, URIRef, Namespace
from posixpath import join
from helper import quote, unquote, url_exists

DATAPATH = 'data'
HTTP = 'http://'
DOMAIN = 'abstractnonsense.net'
STORE = 'Sleepycat'
NAMESPACE = Namespace(join(HTTP, DOMAIN, ''))

ds = Dataset(store=STORE)
ds.open(DATAPATH, create=False) # it stays open all the time, just commits are made

def get_uri(uri):
    global ds # dirty

    ds.commit()
    cg = ConjunctiveGraph(store=STORE)
    cg.open(DATAPATH, create=False)

    # Check URL for existence
    if url_exists(uri, timeout=0.1):
        get_data(uri, ds)

    triple_table = query_union(cg, uri)
    return triple_table

def get_data(uri, dataset):
    coreferences_graph = find_coreferences(uri)
    coreferences = list_coreferences(coreferences_graph)
    update_system_graph(coreferences_graph, dataset) # RDFS and OWL statements go here
    graphs = [dereference(coreference) for coreference in coreferences]
    for graph in graphs:
        dataset.add_graph(graph)
    return None

def find_coreferences(uri):
    '''Accepts URI. Goes to sameas.org, gets triples in the form
    <subject> owl:sameAs <object>, populates a graph with them.

    Returns List.
    '''
    quoted_uri = quote(uri)
    sameas_address_template = 'http://sameas.org/?uri={0}'
    sameas_address = sameas_address_template.format(quoted_uri)

    coreferences_graph = Graph()
    # why n3? because in rdf/xml canonical uri is broken as of 25.10.2013
    coreferences_graph.parse(location=sameas_address, format='n3')

    return coreferences_graph

def list_coreferences(graph):
    query = 'select ?o where { ?s owl:sameAs ?o . }'
    result = graph.query(query)
    coreferences = [row[0] for row in result]
    return coreferences

def update_system_graph(graph, dataset):
    default_graph_name = 'urn:x-rdflib:default'
    system_graph = dataset.get_context(default_graph_name)
    system_graph += graph
    return None

def dereference(uri):
    '''Parse data from `uri`, return triples in form of named graph'''
    graph = Graph(identifier=uri)
    try:
        graph.parse(uri)
        if uri == 'http://dbpedia.org/ontology/Person':
            print 'LOL!', [s for s, p, o in graph]
    except Exception, e:
        # PluginException: No plugin registered for (text/plain,
        # <class 'rdflib.parser.Parser'>)
        print e
    return graph

def query_union(cg, uri):
    '''Query union of graphs to get all triples, where URI is used.

    Returns a 3-tuple of lists.
    '''
    # query_template_subject = '''select ?p ?o
    # where {{
    # <{0}> ?p ?o .
    # }}
    # '''
    # query_template_predicate = '''select ?s ?o
    # where {{
    # ?s <{0}> ?o .
    # }}
    # '''
    # query_template_object = '''select ?s ?p
    # where {{
    # ?s ?p <{0}> .
    # }}
    # '''
    query_template_subject = '''select ?p ?o
    where {{
    {{ <{0}> ?p ?o . }} union
    {{ ?synonym ?p ?o .
       {{ ?synonym owl:sameAs+ <{0}> . }} union
       {{ <{0}> owl:sameAs+ ?synonym . }}
    }}
    }}
    '''
    query_template_predicate = '''select ?s ?o
    where {{
    {{ ?s <{0}> ?o . }} union
    {{ ?s ?synonym ?o .
       {{ ?synonym owl:sameAs+ <{0}> . }} union
       {{ <{0}> owl:sameAs+ ?synonym . }}
    }}
    }}
    '''
    query_template_object = '''select ?s ?p
    where {{
    {{ ?s ?p <{0}> . }} union
    {{ ?s ?p ?synonym .
       {{ ?synonym owl:sameAs+ <{0}> . }} union
       {{ <{0}> owl:sameAs+ ?synonym . }}
    }}
    }}
    '''

    query_subject = query_template_subject.format(uri)
    query_predicate = query_template_predicate.format(uri)
    query_object = query_template_object.format(uri)

    # OWL namespace understood by default
    cg.namespace_manager.bind('owl', 'http://www.w3.org/2002/07/owl#')

    subjects = cg.query(query_subject)
    predicates = cg.query(query_predicate)
    objects = cg.query(query_object)

    return (subjects, predicates, objects)

def get_literal(literal):
    '''Get all triples associated with this literal using a SPARQL query'''
    global ds

    query_template = '''select ?s ?p
    where {{
    ?s ?p "{0}" .
    }}
    '''
    query = query_template.format(literal)
    triples = ds.query(query)

    return triples

def get_graph(uri):
    global ds

    graph = ds.get_context(uri)

    # crude way to dereference URI of the graph, if it doesn't exist
    if not len(graph):
        load_rdf(ds, uri)

    triples = graph.triples((None, None, None))
    return triples

def remove_graph(uri):
    global ds

    ds.remove_context(uri)

    return None
