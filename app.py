from flask import Flask, render_template, request, redirect
from model import get_uri

DEBUG = True
HOST = "127.0.0.1"
PORT = 17000

app = Flask(__name__, static_url_path='')

@app.route('/')
def index():
    return render_template('index.html')

# for some reason route '/<path:uri>' doesn't work, Flask says 404,
# only non-root directory works, like '/page/<path:uri>'
@app.route('/page/<path:uri>')
def article(uri):
    '''Get all information about this URI from KB'''
    subjects, predicates, objects = get_uri(uri)
    return render_template('uri.html',
                           uri=uri,
                           subjects=subjects,
                           predicates=predicates,
                           objects=objects)

if __name__ == '__main__':
    app.run(debug=DEBUG, port=PORT, host=HOST)
