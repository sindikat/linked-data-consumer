'''This script initializes data file, that contains triples'''

from rdflib import Graph

g = Graph()
g.parse('foaf.ttl', format='n3')
g.serialize('data.ttl', format='n3')
