from rdflib import Graph, URIRef
from posixpath import join

DATAFILE = 'data.ttl'
HTTP = 'http://'
# DOMAIN = 'abstractnonsense.net'
DOMAIN = 'localhost:17000'

g = Graph()
# n = Namespace(join(HTTP, DOMAIN, ''))

# Init graph
g.parse(DATAFILE, format='n3')

def get_uri(uri):
    '''get uri as subject using sparql query'''
    global g # dirty

    load_graph = load_rdf(uri)
    g += load_graph
    save(g)

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

    subjects = sparql_query(g, query_subject)
    predicates = sparql_query(g, query_predicate)
    objects = sparql_query(g, query_object)

    return (subjects, predicates, objects)

def sparql_query(graph, query):
    def htmlize(string, href=None):
        '''Add HTML anchor tag'''

        # by default href is equal to string
        if not href:
            href = string

        # replace octothorpe with URL encoding %23
        href = href.replace('#', '%23')

        result = '<a href="' + href + '">' + string + '</a>'
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
                    url = HTTP + DOMAIN + '/page/' + string
                    element_modified = htmlize(string, url)
                else:
                    element_modified = element.toPython()
                row_result.append(element_modified)
            result.append(row_result)

        return result

    result = graph.query(query)

    final = result_to_xss(result)

    return final

def load_rdf(uri):
    '''Accepts URI, returns Graph'''
    new_graph = Graph()
    try:
        print uri
        new_graph.parse(uri)
    except Exception, e:
        print e, type(e)
        pass
    return new_graph

def save(graph):
    '''Serialize graph to Turtle.

    SIDE EFFECTS
    '''
    graph.serialize('data.ttl', format='n3')
    return None
