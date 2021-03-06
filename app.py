from flask import Flask, render_template, request, redirect
from model import start, get_uri, get_literal, get_graph, remove_graph, original
from jinja import update_environment

DEBUG = True
HOST = "127.0.0.1"
PORT = 17000

app = Flask(__name__, static_url_path='')
update_environment(app) # my custom Jinja2 filters

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/original')
def route_original():
    triples = original()
    return render_template('graph.html',
                           graph_name='Original FOAF file',
                           triples=triples)

@app.route('/start')
def route_start():
    quads = start()
    # result_redirect = 'uri/' + result_uri
    return render_template('final.html',
                           header='Result',
                           quads=quads)

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

@app.route('/literal/<path:uri>')
def literal(uri):
    triples = get_literal(uri)
    return render_template('literal.html',
                           uri=uri,
                           rows=triples)

@app.route('/graph/<path:uri>')
def graph(uri):
    triples = get_graph(uri)
    return render_template('graph.html',
                           graph_name=uri,
                           triples=triples)

@app.route('/remove_graph/<path:uri>')
def graph_remove(uri):
    remove_graph(uri)
    return redirect('/')

@app.route('/add_triple/<path:uri>')
def triple_add(uri):
    '''Add a triple to a named graph'''
    return render_template('add_triple.html',
                           graph_name=uri)

if __name__ == '__main__':
    app.run(debug=DEBUG, port=PORT, host=HOST)
