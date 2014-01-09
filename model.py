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

cg = ConjunctiveGraph(store=STORE)
cg.open(DATAPATH, create=False)
# cg.bind('foaf', 'http://xmlns.com/foaf/0.1/') # FOAF namespace understood

# DBPedia workaround
from rdflib.plugin import register, Parser
register('text/rdf+n3', Parser, 'rdflib.plugins.parsers.notation3', 'N3Parser')

def start():
    '''This starts the background script.

    The background script uses a (currently) hardcoded pattern,
    according to which the script harvests data.

    It recursively gathers more and more data, but only to a finite
    depth.

    Return the triples in the form of list of 3-tuples.

    '''
    # initialization of Dataset and ConjunctiveGraph
    global ds, cg # dirty
    ds.bind('abs', NAMESPACE) # namespace for my URIs
    ds.commit()

    # recursively harvest data
    recur(cg, depth=1)

    # return all triples
    wildcard = (None, None, None)
    # triples = cg.triples(wildcard)
    quads = cg.quads(wildcard)
    quads = map(lambda (s, p, o, c): (s, p, o, c.identifier), quads)
    # subjects, predicates, objects = zip(*triples)

    return quads

def recur(cg, depth):
    '''Recursive function for harvesting data.

    It harvests data by dereferencing. It continues to dereference
    URIs, until depth is 0.

    Breadth-first search.
    '''
    if depth == 0:
        return None
    else:
        # get URIs to dereference
        # TODO: change <http://xmlns.com/foaf/0.1/knows> to foaf:knows
        where_clause = '''
        ?x1 <http://xmlns.com/foaf/0.1/knows> ?x2 .
        ?x3 a <http://xmlns.com/foaf/0.1/Person> .
        '''
        query_template = 'select * where {{ {0} }}'
        query = query_template.format(where_clause)
        result = cg.query(query)
        uris = {x for row in result for x in row}
        print uris
        for uri in uris:
            dereference(uri, ds)
            # get_uri(uri)
        return recur(cg, depth-1)

def get_uri(uri):
    '''Returns all triples relevant to the URI.

    In other words, those, which have URI as a Resource.

    If there is no data in the triplestore, tries to harvest data.
    '''
    global ds # dirty

    ds.commit()
    cg = ConjunctiveGraph(store=STORE)
    cg.open(DATAPATH, create=False)

    get_data(uri, ds)

    triple_table = query_union(cg, uri)
    return triple_table

def get_data(uri, dataset):
    '''Finds corefererences, tries to dereference them, creates a named
    graph for each URI.
    '''
    coreferences_graph = find_coreferences(uri)
    coreferences = list_coreferences(coreferences_graph)
    # update_system_graph(coreferences_graph, dataset) # RDFS and OWL statements go here
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
    '''Returns a list of coreferences. Accepts a graph that came from sameas.org.'''
    query = 'select ?o where { ?s owl:sameAs ?o . }'
    result = graph.query(query)
    coreferences = [row[0] for row in result]
    return coreferences

# def update_system_graph(graph, dataset):
#     default_graph_name = 'urn:x-rdflib:default'
#     system_graph = dataset.get_context(default_graph_name)
#     system_graph += graph
#     return None

def dereference(uri, dataset):
    '''Parse data from `uri`, return triples in form of named graph'''
    graph_name = find_named_graph(uri, dataset)
    if graph_name:
        identifier = graph_name
    else:
        identifier = NAMESPACE[join('graph', uuid4().hex)]

    # TODO: check that the graph is properly removed
    graph = dataset.graph(identifier=identifier)

    # Check if URI was dereferenced > 1 day ago
    if check_timestamp(dataset, uri) and url_exists(uri, timeout=5):
        # remove the old graph
        dataset.remove_graph(identifier)
        graph = dataset.graph(identifier=identifier)
        try:
            graph.parse(uri)
        except Exception, e:
            # PluginException: No plugin registered for (text/plain,
            # <class 'rdflib.parser.Parser'>)
            print e

    # timestamp of last download
    update_metagraph(identifier, uri, dataset)

    return graph

def find_named_graph(uri, dataset):
    '''I have a system graph called abs:metagraph. It is a special graph
    that contains metadata about other named graphs.

    The metadata is the last time a URI was accessed and which named
    graph corresponds to which URI.
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
    '''Update a metagraph, which contains metadata about the named graphs.

    Namely, create triples that relate a named graph with a
    corresponding URI, and timestamp, when the URI was dereferenced.
    '''
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

    if result.bindings:
        date = result.bindings[0]['date'].toPython()
        timedelta = datetime.now() - date
        if timedelta.days >= 1:
            return True
        else:
            return False
    else:
        return True

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
    # TODO: move to the global scope?
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

    triples = graph.triples((None, None, None))
    return triples

def remove_graph(uri):
    global ds

    ds.remove_context(uri)

    return None

def original():
    '''Returns a named graph that corresponds to an original FOAF file.

    '''
    global ds
    foaf_graph_name = 'http://abstractnonsense.net/graph/i'
    g = ds.graph(identifier=foaf_graph_name)
    return g
