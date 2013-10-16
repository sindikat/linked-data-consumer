'''Helper functions'''
import urllib

def quote(string):
    '''My version of urllib.quote. Encodes to ASCII automatically.
    '''
    # assume utf-8 encoding
    if isinstance(string, unicode):
        encoded_string = string.encode('utf-8')

    # example: # -> %23
    quoted_string = urllib.quote(encoded_string, safe='/:')

    return quoted_string

def unquote(string):
    '''Alias for urllib.unquote'''
    return urllib.unquote(string)
