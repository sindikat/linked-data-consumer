from flask import Flask, render_template, request, redirect
from model import get_uri, get_graph

DEBUG = True
HOST = "127.0.0.1"
PORT = 17000

app = Flask(__name__, static_url_path='')

@app.route('/')
def index():
    return render_template('index.html')

# '/<path:uri>' doesn't work because of static_url_path, think
@app.route('/uri/<path:uri>')
def resource(uri):
    '''Get all information about this URI from KB'''
    subjects, predicates, objects = get_uri(uri)
    return render_template('uri.html',
                           uri=uri,
                           subjects=subjects,
                           predicates=predicates,
                           objects=objects)

@app.route('/graph/<path:uri>')
def graph(uri):
    triples = get_graph(uri)
    return render_template('graph.html',
                           graph_name=uri,
                           triples=triples)

if __name__ == '__main__':
    app.run(debug=DEBUG, port=PORT, host=HOST)
