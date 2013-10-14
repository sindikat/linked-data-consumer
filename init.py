'''This script initializes data file, that contains triples'''

from rdflib import Graph, ConjunctiveGraph
from shutil import rmtree
from os.path import exists

DATAPATH = 'data'
DOMAIN = 'http://abstractnonsense.net/'
DEFAULT_GRAPH = DOMAIN + 'i'

def remove_data(datapath):
    '''SIDE EFFECTS'''
    if exists(datapath):
        rmtree(datapath)
    return None

cg = ConjunctiveGraph(store='Sleepycat')
remove_data(DATAPATH)
cg.open('data', create=True)
g = cg.get_context(identifier=DEFAULT_GRAPH)
g.parse('foaf.ttl', format='n3')
cg.close()
