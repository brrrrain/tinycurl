#encoding: utf-8
import sys
import time
import logging
import urlparse
import urllib
import pycurl
from StringIO import StringIO
from pprint import pprint
from tinycurl_exceptions import DeadProxy, WrongCode, InfiniteRedirection

MAX_REDIRECTS = 2
TIMEOUT = 1
HAMMER_MODE_ATTEMPTS = 3
PROXY_TYPE = 'socks5'

def __headers_to_dict(headers):
    """ 
    Получаем: ("Connection: Keep-Alive", )
    Отдаём: {"Connection": "Keep-Alive"}
    """

    keys, values = [], []
    result = {}
    for item in headers:
        try:
            key, value = item.split(': ')
        except ValueError as e:
            continue

        if key in result.keys():
            result[key] += '\r\n' + value
        else:
            result[key] = value

    return result

def __get_headers(data):
    """
    Получаем текстовый набор(ы) заголовков:
    Blabla: blabla\r\n
    Blabla2: blabla2\r\n\r\n

    Отдаём словарь:
    {"Blabla": 'blabla', etc.}
    """
    data = data.strip()

    #Мы можем иметь несколько наборов заголовков т.к один ответ может 
    #быть просто редиректом, поэтому возвращаем всегда последний набор 
    #заголовков;
    #
    #УТОЧНЕНИЕ: описание актуально при использовании опции FOLLOWLOCATION;
    #При отключении данной опции, набор заголовков всегда один
    headers_list = data.split('\r\n\r\n', 1)[-1]
    headers_list = headers_list.split('\r\n')
    headers_list = [item for item in headers_list if item]

    headers_dict = __headers_to_dict(headers_list)

    if 'Set-Cookie' not in headers_dict.keys():
        headers_dict['Set-Cookie'] = ''

    return headers_dict

def __logging(debug_type, debug_msg):
    #debug_type = 3 — это тело ответа
    if debug_type != 3:
        logging.debug("debug(%d): %s" % (debug_type, debug_msg.strip()))

def __query_to_dict(query):
    """
    На входе: a=1&b=2
    На выходе словарь: {'a': 1, 'b': 2}
    """
    return dict(urlparse.parse_qsl(query))

def __get_cookies(set_cookie_string, current_cookies=''):
    """
    На входе: заголовок Set-Cookie: a=1; domain=blabla.com; ....
              уже используемые куки: b=2&c=3

    На выходе: a=1&b=2&c=3
    Существующие куки обновляют данные при наличие таковых в
    новых куки
    """
    cookies_list = set_cookie_string.split('\r\n')
    current_cookies = __query_to_dict(current_cookies)
    cookies = {}

    for item in cookies_list:
        try:
            item = item.split(';')[0]
            name, val = item.split('=', 1)

            #если значение куки пустое или равно deleted
            #то удаляем куку
            if val == 'deleted' or not val:
                try:
                    del current_cookies[name]
                except KeyError:
                    pass

                continue

            cookies[name] = val
        except ValueError:
            continue

    cookies.update(current_cookies)  

    return urllib.unquote(urllib.urlencode(cookies)) 

def __request(url, request_type, cookies='', post_data={}, proxy=None, 
              redirect_count=0, attempt=1):
    """
    Универсальная функция. Используется в функциях get & post
    Возвращает: 
        Словарь заголовков: dict
        Тело: string
        Cookies: string; query string: a=1&b=2
        Connect time: float
        Current URL: string
        Redirect URL: string | none
        Redirect count: integer
    """
    c = pycurl.Curl()

    headers = StringIO()
    body = StringIO()

    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.TIMEOUT, TIMEOUT)
    c.setopt(pycurl.WRITEFUNCTION, body.write)
    c.setopt(pycurl.HEADERFUNCTION, headers.write)

    #Если код ответа >= 400, то вызываем ошибку
    c.setopt(pycurl.FAILONERROR, 1)

    #ВАЖНО: т.к. куки не сохраняем в файлах, а передаём строкой
    #то FOLLOWLOCATION не будет использовать куки, присвоенные 
    #сразу до редиректа. Отказываемся от его использования
    #
    #c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.COOKIE, cookies)
    c.setopt(pycurl.VERBOSE, 1)
    c.setopt(pycurl.DEBUGFUNCTION, __logging)

    if request_type.lower() == 'post' and post_data:
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, urllib.urlencode(post_data))

    #Если передан прокси, то работаем через него
    if proxy:
        #CURL proxytype
        if PROXY_TYPE == 'socks5':
            proxy_type = pycurl.PROXYTYPE_SOCKS5
        elif PROXY_TYPE == 'socks4':
            proxy_type = pycurl.PROXYTYPE_SOCKS4
        elif PROXY_TYPE == 'http':
            proxy_type = pycurl.PROXYTYPE_HTTP

        #если не можем отделить ip и порт, то возвращаем ошибку
        try:
            proxy_ip, port = proxy.split(':')
            port = int(port)
        except ValueError, e:
            logging.error("Возможно, неверный формат прокси: %s", str(proxy))
            raise DeadProxy(proxy_ip, port)

        c.setopt(pycurl.PROXY, proxy_ip)
        c.setopt(pycurl.PROXYPORT, port)
        c.setopt(pycurl.PROXYTYPE, proxy_type)

    #Обработка исключений при загрузке страницы
    try:
        c.perform()
    except pycurl.error as err:
        """
        CURLE_HTTP_RETURNED_ERROR (22)
        This is returned if CURLOPT_FAILONERROR is set TRUE and the HTTP 
        server returns an error code that is >= 400. 
        """
        if err[0] == 22:
            raise WrongCode(c.getinfo(pycurl.RESPONSE_CODE))

        """
        Если используем прокси, то все ошибки, кроме неверного кода ответа
        спихиваем на него
        """
        if proxy:
            raise DeadProxy(proxy_ip, port)
        else:
            raise pycurl.error(str(err))

    #словарь
    headers = __get_headers(headers.getvalue())

    result = {'headers': headers, 
              'body': body.getvalue(),
              'current_proxy': proxy,
              'cookies': __get_cookies(headers['Set-Cookie']),
              'connect_time': c.getinfo(pycurl.CONNECT_TIME),
              'response_code': c.getinfo(pycurl.RESPONSE_CODE),
              'current_url': c.getinfo(pycurl.EFFECTIVE_URL),
              'redirect_url': c.getinfo(pycurl.REDIRECT_URL),
              'redirect_count': redirect_count} 
    c.close()
    del c

    return result

def __process_redirect(result):
    """
    Если в результате запроса присутствует redirect_url
    то вызываем функцию get c текущими куки;
    Оборачиваем текущей функцией функцию __request в функциях
    post или get
    """
    if result['redirect_url']:
        result['redirect_count'] += 1
        result = get(result['redirect_url'], result['cookies'], 
                     redirect_count=result['redirect_count'], 
                     proxy=result['current_proxy'])

    return result

def get(url, cookies='', proxy=None, redirect_count=0):
    """
    GET запрос
    Возвращаемые значения: см. функцию __request
    """
    err_counter = 0

    if redirect_count >= MAX_REDIRECTS:
        raise InfiniteRedirection(url)

    #Бесконечный цикл для hammer mode
    while True:

        try:
            result = __process_redirect(__request(url, request_type='get', 
                                                  cookies=cookies, 
                                                  proxy=proxy,
                                                  redirect_count=redirect_count))
            return result

        except DeadProxy as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise DeadProxy(e['proxy'], e['port'])

        except pycurl.error as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise pycurl.error(str(e))

def post(url, data, cookies='', proxy=None):
    """
    POST запрос
    data: dict
    Возвращаемые значения: см. функцию __request
    """
    err_counter = 0

    #Бесконечный цикл для hammer mode
    while True:
        try:
            result = __process_redirect(__request(url, request_type='post', 
                                                  cookies=cookies, post_data=data,
                                                  proxy=proxy))
            return result
        except DeadProxy as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise DeadProxy(e['proxy'], e['port'])

        except pycurl.error as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise pycurl.error(str(e))


#TODO: возврат значений в неудавшихся запросах
