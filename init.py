'''This script initializes data file, that contains triples'''

from rdflib import Dataset

DOMAIN = 'http://abstractnonsense.net/'
DEFAULT_GRAPH = DOMAIN + 'i'

ds = Dataset('Sleepycat')
ds.open('data', create=True)
g = ds.graph(DEFAULT_GRAPH)
g.parse('foaf.ttl', format='n3')
ds.close()
