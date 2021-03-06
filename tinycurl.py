# encoding: utf-8
import logging
import urlparse
import urllib
import pycurl
from StringIO import StringIO
from tinycurl_exceptions import DeadProxy, WrongCode, InfiniteRedirection

MAX_REDIRECTS = 2
TIMEOUT = 1
HAMMER_MODE_ATTEMPTS = 3
PROXY_TYPE = 'socks5'
HEADERS = []
USERAGENT = ''


def __headers_to_dict(headers, replace_duplicates=False):
    """
    Получаем: ("Connection: Keep-Alive", )
    Отдаём: {"Connection": "Keep-Alive"}
    """

    keys, values = [], []
    result = {}
    for item in headers:
        try:
            key, value = item.split(': ')
        except ValueError:
            continue

        if key in result.keys() and replace_duplicates is False:
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

    # Мы можем иметь несколько наборов заголовков т.к один ответ может
    # быть просто редиректом, поэтому возвращаем всегда последний набор
    # заголовков;
    #
    # УТОЧНЕНИЕ: описание актуально при использовании опции FOLLOWLOCATION;
    # При отключении данной опции, набор заголовков всегда один
    headers_list = data.split('\r\n\r\n', 1)[-1]
    headers_list = headers_list.split('\r\n')
    headers_list = [item for item in headers_list if item]

    headers_dict = __headers_to_dict(headers_list)

    if 'Set-Cookie' not in headers_dict.keys():
        headers_dict['Set-Cookie'] = ''

    return headers_dict


def __logging(debug_type, debug_msg):
    # debug_type = 3 — это тело ответа
    if debug_type != 3:
        logging.debug("debug(%d): %s" % (debug_type, debug_msg.strip()))


def __query_to_dict(query):
    """
    На входе: a=1&b=2
    На выходе словарь: {'a': 1, 'b': 2}
    """
    query = query.replace('; ', '&')
    return dict(urlparse.parse_qsl(query))


def __get_cookies(set_cookie_string, current_cookies=''):
    """
    На входе: заголовок Set-Cookie: a=1; domain=blabla.com; ....
              уже используемые куки: b=2; c=3

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

            # если значение куки пустое или равно deleted
            # то удаляем куку
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

    return urllib.unquote(urllib.urlencode(cookies)).replace('&', '; ')


def __request(url, request_type, cookies='', post_data={}, proxy=None,
              headers=[], useragent='', referer='', redirect_count=0,
              attempt=1, headers_only=False):
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

    # сливаем переданые в функции и глобальные заголовки
    all_headers = HEADERS + headers
    all_headers = __headers_to_dict(all_headers, replace_duplicates=True)
    all_headers = ["%s: %s" % (k, v) for k, v in all_headers.items()]

    c = pycurl.Curl()

    got_headers = StringIO()
    body = StringIO()

    if headers_only:
        c.setopt(pycurl.NOBODY, 1)
    else:
        c.setopt(pycurl.WRITEFUNCTION, body.write)

    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.TIMEOUT, TIMEOUT)
    c.setopt(pycurl.HEADERFUNCTION, got_headers.write)

    """
    If it is 1, libcurl will not use any functions that install signal
    handlers or any functions that cause signals to be sent to the
    process. This option is mainly here to allow multi-threaded unix
    applications to still set/use all timeout options etc, without risking
    getting signals
    """
    c.setopt(pycurl.NOSIGNAL, 1)

    # более приоритетный юзер-агент - это переданый в функцию
    # менее приоритетный - это юзер-агент установленный глобально
    if not useragent:
        if USERAGENT:
            useragent = USERAGENT

    if useragent:
        c.setopt(pycurl.USERAGENT, useragent)

    if all_headers:
        c.setopt(pycurl.HTTPHEADER, all_headers)

    # Установка referer'a
    if referer:
        c.setopt(pycurl.REFERER, referer)


    # Если код ответа >= 400, то вызываем ошибку
    c.setopt(pycurl.FAILONERROR, 1)

    # ВАЖНО: т.к. куки не сохраняем в файлах, а передаём строкой
    # то FOLLOWLOCATION не будет использовать куки, присвоенные
    # сразу до редиректа. Отказываемся от его использования
    #
    # c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.COOKIE, cookies)
    c.setopt(pycurl.VERBOSE, 1)
    c.setopt(pycurl.DEBUGFUNCTION, __logging)

    # не проверяем SSL сертификат. Запросы становястя уязвимы к атаке MITM
    c.setopt(pycurl.SSL_VERIFYHOST, 0)
    c.setopt(pycurl.SSL_VERIFYPEER, 0)

    if request_type.lower() == 'post' and post_data:
        c.setopt(pycurl.HTTPPOST, post_data.items())

    # Если передан прокси, то работаем через него
    if proxy:
        # CURL proxytype
        if PROXY_TYPE == 'socks5':
            proxy_type = pycurl.PROXYTYPE_SOCKS5
        elif PROXY_TYPE == 'socks4':
            proxy_type = pycurl.PROXYTYPE_SOCKS4
        elif PROXY_TYPE == 'http':
            proxy_type = pycurl.PROXYTYPE_HTTP

        # если не можем отделить ip и порт, то возвращаем ошибку
        try:
            proxy_ip, port = proxy.split(':')
            port = int(port)
        except ValueError:
            logging.error("Возможно, неверный формат прокси: %s", str(proxy))
            raise DeadProxy(proxy_ip, port)

        c.setopt(pycurl.PROXY, proxy_ip)
        c.setopt(pycurl.PROXYPORT, port)
        c.setopt(pycurl.PROXYTYPE, proxy_type)

    # Обработка исключений при загрузке страницы
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

    # словарь
    got_headers = __get_headers(got_headers.getvalue())

    result = {'headers': got_headers,
              'body': body.getvalue(),
              'current_proxy': proxy,
              'useragent': useragent,
              'referer': referer,
              'sent_headers': all_headers,
              'cookies': __get_cookies(got_headers['Set-Cookie'], cookies),
              'connect_time': c.getinfo(pycurl.CONNECT_TIME),
              'response_code': c.getinfo(pycurl.RESPONSE_CODE),
              'current_url': c.getinfo(pycurl.EFFECTIVE_URL),
              'redirect_url': c.getinfo(pycurl.REDIRECT_URL),
              'redirect_count': redirect_count,
              'headers_only': headers_only}
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
                     proxy=result['current_proxy'],
                     referer=result['referer'],
                     useragent=result['useragent'],
                     headers=result['sent_headers'],
                     headers_only=result['headers_only'])

    return result


def get(url, cookies='', proxy=None, useragent='', referer='',
        headers=[], redirect_count=0, headers_only=False):
    """
    GET запрос
    Возвращаемые значения: см. функцию __request
    """
    err_counter = 0

    if redirect_count >= MAX_REDIRECTS:
        raise InfiniteRedirection(url)

    # Бесконечный цикл для hammer mode
    while True:

        try:
            result = __process_redirect(__request(url, request_type='get',
                                                  cookies=cookies,
                                                  proxy=proxy,
                                                  referer=referer,
                                                  useragent=useragent,
                                                  headers=headers,
                                                  redirect_count=redirect_count,
                                                  headers_only=headers_only))
            return result

        except DeadProxy as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise DeadProxy(e['proxy'], e['port'])

        except pycurl.error as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise pycurl.error(str(e))


def post(url, data, cookies='', proxy=None, useragent='', referer='',
         headers=[], headers_only=False):
    """
    POST запрос
    data: dict
    Возвращаемые значения: см. функцию __request
    """
    err_counter = 0

    # Бесконечный цикл для hammer mode
    while True:
        try:
            result = __process_redirect(__request(url, request_type='post',
                                                  cookies=cookies,
                                                  referer=referer,
                                                  post_data=data,
                                                  useragent=useragent,
                                                  headers=headers,
                                                  proxy=proxy,
                                                  headers_only=headers_only))
            return result
        except DeadProxy as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise DeadProxy(e['proxy'], e['port'])

        except pycurl.error as e:
            err_counter += 1
            if err_counter >= HAMMER_MODE_ATTEMPTS:
                raise pycurl.error(str(e))
