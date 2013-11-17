from rdflib import Graph, ConjunctiveGraph, Dataset, URIRef, Namespace, Literal
from posixpath import join
from uuid import uuid4
from datetime import datetime
from helper import quote, unquote, url_exists

DATAPATH = 'data'
HTTP = 'http://'
DOMAIN = 'abstractnonsense.net'
STORE = 'Sleepycat'
NAMESPACE = Namespace(join(HTTP, DOMAIN, ''))

ds = Dataset(store=STORE)
ds.open(DATAPATH, create=False) # it stays open all the time, just commits are made
ds.bind('abs', NAMESPACE) # namespace for my URIs

# DBPedia workaround
from rdflib.plugin import register, Parser
register('text/rdf+n3', Parser, 'rdflib.plugins.parsers.notation3', 'N3Parser')

def start():
    # initialization of Dataset and ConjunctiveGraph
    global ds # dirty
    ds.commit()
    cg = ConjunctiveGraph(store=STORE)
    cg.open(DATAPATH, create=False)

    # get all URIs and try to dereference them
    uris = {x for x in cg.all_nodes() if isinstance(x, URIRef)}

    print uris

    return join(HTTP, DOMAIN, 'i')

def get_uri(uri):
    global ds # dirty

    ds.commit()
    cg = ConjunctiveGraph(store=STORE)
    cg.open(DATAPATH, create=False)

    get_data(uri, ds)

    triple_table = query_union(cg, uri)
    return triple_table

def get_data(uri, dataset):
    coreferences_graph = find_coreferences(uri)
    coreferences = list_coreferences(coreferences_graph)
    update_system_graph(coreferences_graph, dataset) # RDFS and OWL statements go here
    graphs = [dereference(coreference, dataset) for coreference in coreferences]
    for graph in graphs:
        # without this if the graphs with same id are repeated
        if graph not in dataset.contexts():
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

def dereference(uri, dataset):
    '''Parse data from `uri`, return triples in form of named graph'''
    graph_name = find_named_graph(uri, dataset)
    if graph_name:
        identifier = graph_name
    else:
        identifier = NAMESPACE[join('graph', uuid4().hex)]
        update_metagraph(identifier, uri, dataset)

    # TODO: check that the graph is properly removed
    graph = dataset.graph(identifier=identifier)

    # Check if URI was dereferenced > 1 day ago
    if check_timestamp(dataset, uri) and url_exists(uri, timeout=2):
        # remove the old graph
        dataset.remove_graph(identifier)
        graph = dataset.graph(identifier=identifier)
        try:
            graph.parse(uri)
        except Exception, e:
            # PluginException: No plugin registered for (text/plain,
            # <class 'rdflib.parser.Parser'>)
            print e

    return graph

def find_named_graph(uri, dataset):
    '''I have a system graph called abs:metagraph. It is a special graph
    that contains metadata about other named graphs.
    '''
    metagraph_id = NAMESPACE.metagraph
    metagraph = dataset.graph(metagraph_id)
    query_template = 'select ?graph where {{ ?graph abs:uri <{0}> }}'
    query = query_template.format(uri)
    result = metagraph.query(query)
    if result:
        return result.bindings[0]['graph']
    else:
        return None

def update_metagraph(identifier, uri, dataset):
    identifier = URIRef(identifier)
    uri = URIRef(uri)

    # special properties, related to named graphs
    p_uri = NAMESPACE.uri
    p_date = NAMESPACE.last_downloaded

    date = Literal(datetime.now())

    metagraph_id = NAMESPACE.metagraph
    metagraph = dataset.graph(metagraph_id)
    triple_name = (identifier, p_uri, uri)
    metagraph.remove((uri, p_date, None)) # remove old timestamp
    triple_date = (uri, p_date, date)
    metagraph.add(triple_name)
    metagraph.add(triple_date)
    return None

def check_timestamp(dataset, uri):
    '''Checks the timestamp of the named graph'''
    metagraph_id = NAMESPACE.metagraph
    metagraph = dataset.graph(metagraph_id)

    query_template = 'select ?date where {{ <{0}> abs:last_downloaded ?date . }}'
    query = query_template.format(uri)

    result = metagraph.query(query)
    date = result.bindings[0]['date'].toPython()

    timedelta = datetime.now() - date
    if timedelta.days >= 1:
        return True
    else:
        return False

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
    query_template_subject = '''select distinct ?p ?o
    where {{
    {{ <{0}> ?p ?o . }} union
    {{ ?synonym ?p ?o .
       {{ ?synonym owl:sameAs* <{0}> . }} union
       {{ <{0}> owl:sameAs* ?synonym . }}
    }}
    }}
    '''
    query_template_predicate = '''select distinct ?s ?o
    where {{
    {{ ?s <{0}> ?o . }} union
    {{ ?s ?synonym ?o .
       {{ ?synonym owl:sameAs* <{0}> . }} union
       {{ <{0}> owl:sameAs* ?synonym . }}
    }}
    }}
    '''
    query_template_object = '''select distinct ?s ?p
    where {{
    {{ ?s ?p <{0}> . }} union
    {{ ?s ?p ?synonym .
       {{ ?synonym owl:sameAs* <{0}> . }} union
       {{ <{0}> owl:sameAs* ?synonym . }}
    }}
    }}
    '''

    query_subject = query_template_subject.format(uri)
    query_predicate = query_template_predicate.format(uri)
    query_object = query_template_object.format(uri)

    # OWL namespace understood by default
    cg.bind('owl', 'http://www.w3.org/2002/07/owl#')

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
