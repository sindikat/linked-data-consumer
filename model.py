from rdflib import Graph, ConjunctiveGraph, URIRef
from posixpath import join
from urllib import quote, unquote

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

def sparql_query(graph, query):
    def htmlize(string, href=None):
        '''Add HTML anchor tag'''

        # by default href is equal to string
        if not href:
            href = string

        # assume utf-8 encoding
        if isinstance(href, unicode):
            href = href.encode('utf-8')
        # replace octothorpe with URL encoding %23
        href = quote(href, safe='/:')

        result = '<a href="' + href + '">' + string + '</a>'
        print result
        return result

    def result_to_xss(query_result):
        '''convert rdflib.query.Result to list of lists'''
        # there's also query_result.bindings
        result = []

        for row in query_result:
            row_result = []
            for element in row:
                # URIRef to <a>, Literal to just string
                if isinstance(element, URIRef):
                    string = element.toPython()
                    url = HTTP + DOMAIN + '/uri/' + string
                    element_modified = htmlize(string, url)
                else:
                    element_modified = element.toPython()
                row_result.append(element_modified)
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
