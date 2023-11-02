import string




def clean_text_de(string):
    return remove_umlaut(string)

def remove_umlaut(string):
    """
    Removes umlauts from strings and replaces them with the letter+e convention
    :param string: string to remove umlauts from
    :return: unumlauted string
    """
    u = 'ü'.encode()
    U = 'Ü'.encode()
    a = 'ä'.encode()
    A = 'Ä'.encode()
    o = 'ö'.encode()
    O = 'Ö'.encode()
    ss = 'ß'.encode()

    string = string.encode()
    string = string.replace(u, b'u')
    string = string.replace(a, b'a')
    string = string.replace(o, b'o')
    string = string.replace(ss, b'ss')

    string = string.decode('utf-8')
    return string
