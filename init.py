'''This script initializes data file, that contains triples'''

from rdflib import Graph

g = Graph('Sleepycat')
g.open('data', create=True)
g.parse('foaf.ttl', format='n3')
g.close()
