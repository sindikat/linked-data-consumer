'''These are custom filters for Jinja 2
'''

from helper import quote, unquote

jinja_quote = quote
jinja_unquote = unquote

def update_environment(app):
    '''Receives Flask app and updates its Jinja environment with my custom
    filters.
    '''
    app.jinja_env.filters.update({'quote': jinja_quote, 'unquote': jinja_unquote})
    return None
