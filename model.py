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
    if url_exists(uri, timeout=1):
        get_data(uri, ds)

    triple_table = query_union(cg, uri)
    # print cg.query('select ?p where { <http://google.com> ?p ?o . }')[0]
    return triple_table

def get_data(uri, dataset):
    coreferences_graph = find_coreferences(uri)
    canonical_uri = get_canonical_uri(coreferences_graph)
    coreferences = list_coreferences(coreferences_graph)
    graphs = dereference(dataset, coreferences) # contains data from coreferences
    final_graph = replace_uris(canonical_uri, graphs)
    print canonical_uri
    print list(ds.contexts())
    dataset.remove_graph(canonical_uri) # remove previous named graph
    dataset.add_graph(final_graph)
    return None

def find_coreferences(uri):
    '''Accepts URI. Goes to sameas.org, gets triples in the form
    <subject> owl:sameAs <object>, populates a graph with them.

    Returns Graph.
    '''
    quoted_uri = quote(uri)
    sameas_address_template = 'http://sameas.org/?uri={0}'
    sameas_address = sameas_address_template.format(quoted_uri)

    coreferences_graph = Graph()
    # why n3? because in rdf/xml canonical uri is broken as of 25.10.2013
    coreferences_graph.parse(location=sameas_address, format='n3')

    return coreferences_graph

def list_coreferences(graph):
    '''Returns a list of URIs that have an owl:sameAs relationship'''
    query = 'select ?o where {{ ?s owl:sameAs ?o . }}'
    result = graph.query(query)
    coreferences = [row[0] for row in result]
    return coreferences

def dereference(dataset, coreferences):
    '''Accepts a Dataset and a list of URIs.

    Creates many named graphs
    after URIs and populates them with data gathered thru
    dereference.
    '''
    graphs = []
    # now dereference every URI
    for uri in coreferences:
        print 'uri', uri
        new_graph = Graph(identifier=uri)
        try:
            new_graph.parse(uri)
        except Exception, e:
            # PluginException: No plugin registered for (text/plain,
            # <class 'rdflib.parser.Parser'>)
            print e
        graphs.append(new_graph)
    return graphs

def get_canonical_uri(graph):
    query = 'select ?canonical where { ?canonical owl:sameAs ?object } limit 1'
    result = graph.query(query)
    canonical_uri = result.bindings[0]['canonical']
    return canonical_uri

def replace_uris(canonical_uri, source_graphs):
    canonical_graph = Graph(identifier=canonical_uri)
    query_template = '''construct {{ <{0}> ?p ?o . ?s <{0}> ?o . ?s ?p <{0}> . }}
    where {{
    optional {{
    <{1}> ?p ?o .
    }}
    optional {{
    ?s <{1}> ?o .
    }}
    optional {{
    ?s ?p <{1}> .
    }}
    }}
    '''
    for graph in source_graphs:
        query = query_template.format(canonical_uri, graph.identifier)
        result = graph.query(query)
        for triple in result: # add to canonical
            canonical_graph.add(triple)
    return canonical_graph

def query_union(cg, uri):
    '''Query union of graphs to get all triples, where URI is used.

    Returns a 3-tuple of lists.
    '''
    query_template_subject = '''select ?p ?o
    where {{
    <{0}> ?p ?o .
    }}
    '''
    query_template_predicate = '''select ?s ?o
    where {{
    ?s <{0}> ?o .
    }}
    '''
    query_template_object = '''select ?s ?p
    where {{
    ?s ?p <{0}> .
    }}
    '''

    query_subject = query_template_subject.format(uri)
    query_predicate = query_template_predicate.format(uri)
    query_object = query_template_object.format(uri)

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

    graph = ds.graph(uri)

    # crude way to dereference URI of the graph, if it doesn't exist
    if not len(graph):
        load_rdf(ds, uri)

    triples = graph.triples((None, None, None))
    return triples

def remove_graph(uri):
    global ds

    ds.remove_context(uri)

    return None

# def find_sameas(uri):
#     def get_canonical_uri(graph):
#         variable = 'canonical'
#         query_template = 'select ?{0} where {{ ?{0} owl:sameAs ?object }} limit 1'
#         query = query_template.format(variable)
#         result = g.query(query)
#         canonical_uri = result.bindings[0][variable]
#         return canonical_uri

#     global ds

#     sameas_address_template = 'http://sameas.org/?uri={0}'
#     sameas_address = sameas_address_template.format(uri)
#     graph_name = join('sameas', uri)
#     g = ds.get_context(NAMESPACE[graph_name])
#     g.parse(sameas_address)

#     canonical_uri = get_canonical_uri(g)

#     query_template = '''select ?o where {{ <{0}> owl:sameAs ?o . }}'''
#     query = query_template.format(canonical_uri)
#     objects = map(lambda row: list(row)[0], g.query(query))

#     # now dereference every URI
#     for new_uri in objects:
#         new_graph = ds.get_context(new_uri)
#         try:
#             new_graph.parse(new_uri)
#         except Exception, e:
#             # PluginException: No plugin registered for (text/plain, <class 'rdflib.parser.Parser'>)
#             print e

#     # now add all data to canonical graph

#     return None

def load_rdf(ds, uri):
    '''Accepts Dataset and URI (as string), returns None.

    SIDE EFFECTS
    '''
    uri_unquoted = unquote(uri)
    graph_identifier = URIRef(uri_unquoted)
    new_graph = ds.graph(graph_identifier)
    try:
        new_graph.parse(uri)
    except Exception, e:
        print e, type(e)
        pass
    return None
