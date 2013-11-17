'''This script initializes data file, that contains triples'''

from rdflib import Graph, Dataset
from shutil import rmtree
from os.path import exists
from model import update_metagraph

DATAPATH = 'data'
DOMAIN = 'http://abstractnonsense.net/'
GRAPH_NAMESPACE = DOMAIN + 'graph' + '/'
DEFAULT_URI = DOMAIN + 'i'
DEFAULT_GRAPH = GRAPH_NAMESPACE + 'i'

def remove_data(datapath):
    '''SIDE EFFECTS'''
    if exists(datapath):
        rmtree(datapath)
    return None

ds = Dataset(store='Sleepycat')
remove_data(DATAPATH)
ds.open('data', create=True)
g = ds.get_context(identifier=DEFAULT_GRAPH)
g.parse('foaf.ttl', format='n3')

update_metagraph(DEFAULT_GRAPH, DEFAULT_URI, ds)

ds.close()
