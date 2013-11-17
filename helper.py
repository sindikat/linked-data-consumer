'''Helper functions'''
import urllib, requests

def quote(string):
    '''My version of urllib.quote. Encodes to ASCII automatically.
    '''
    # assume utf-8 encoding
    if isinstance(string, unicode):
        string = string.encode('utf-8')

    # example: # -> %23
    quoted_string = urllib.quote(string, safe='/:')

    return quoted_string

def unquote(string):
    '''Alias for urllib.unquote'''
    return urllib.unquote(string)

def url_exists(url, timeout=None):
    '''Returns True if status code is 200, 301, 302, 303'''
    try:
        r = requests.head(url, timeout=timeout)
    except Exception:
        return False
    return r.status_code in (200, 301, 302, 303)
