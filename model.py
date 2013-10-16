from rdflib import Graph, ConjunctiveGraph, URIRef
from posixpath import join
from helper import quote, unquote

DATAPATH = 'data'
HTTP = 'http://'
# DOMAIN = 'abstractnonsense.net'
DOMAIN = 'localhost:17000'
STORE = 'Sleepycat'
# NAMESPACE = Namespace(join(HTTP, DOMAIN, ''))

cg = ConjunctiveGraph(store=STORE)
cg.open(DATAPATH, create=False) # it stays open all the time, just commits are made

def get_uri(uri):
    '''get uri as subject using sparql query'''
    global cg # dirty

    load_rdf(cg, uri) # SIDE EFFECTS
    cg.commit() # SIDE EFFECTS

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

    subjects = sparql_query(cg, query_subject)
    predicates = sparql_query(cg, query_predicate)
    objects = sparql_query(cg, query_object)

    return (subjects, predicates, objects)

def get_literal(literal):
    '''Get all triples associated with this literal using a SPARQL query'''
    global cg

    query_template = '''select ?s ?p
    where {{
    ?s ?p "{0}" .
    }}
    '''
    query = query_template.format(literal)
    triples = sparql_query(cg, query)

    return triples

def get_graph(uri):
    global cg

    graph = cg.get_context(uri)
    triples = graph.triples((None, None, None))
    # URIRef & Literal -> string
    # triples_pythonic = map(lambda triple: map(lambda resource: resource.toPython(),
    #                                      triple),
    #                        triples)
    triples_pythonic = triples
    return triples_pythonic

def sparql_query(graph, query):
    def result_to_xss(query_result):
        '''convert rdflib.query.Result to list of lists'''
        # there's also query_result.bindings
        result = []

        for row in query_result:
            row_result = []
            for element in row:
                row_result.append(element)
            result.append(row_result)

        return result

    result = graph.query(query)

    final = result_to_xss(result)

    return final

def load_rdf(cg, uri):
    '''Accepts ConjunctiveGraph and URI (as string), returns None.

    SIDE EFFECTS
    '''
    uri_unquoted = unquote(uri)
    graph_identifier = URIRef(uri_unquoted)
    new_graph = cg.get_context(graph_identifier)
    try:
        new_graph.parse(uri)
    except Exception, e:
        print e, type(e)
        pass
    return None
