#encoding: utf-8

class WrongCode(Exception):
    """
    Вызывать если код ответа >= 400
    """
    def __init__(self, code):
        self.code = code

    def __str__(self):
        return str(self.code)

    def __int__(self):
        return str(self.code)


class InfiniteRedirection(Exception):
    """
    Бесконечная переадресация
    """
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return str(self.url)


class DeadProxy(Exception):
    """
    Вызывать при неудачном соединении (соединениях: hammer mode)
    Строка: айпи:порт
    Обращение к словарю:
        proxy: IP
        port: порт
    """
    def __init__(self, proxy, port):
        self.proxy = proxy
        self.port = port

    def __str__(self):
        return "%s:%s" % (self.proxy, self.port)

    def __getitem__(self, name):
        if name == 'proxy':
            return self.proxy
        elif name == 'port':
            return int(self.port)
        else:
            return None
