#encoding: utf-8
import time
import unittest
import logging
import pycurl
import tinycurl
from tinycurl_exceptions import DeadProxy, WrongCode

import bottle
import curlpretty
import controllers

#TODO: собрать в пакет, начать писать avito спамер

class TestLoadPages(unittest.TestCase):
    def setUp(self):
        self.mock_curl = curlpretty.curlpretty(controllers)
        self.mock_curl.mock()
        tinycurl.TIMEOUT = 1
        tinycurl.HAMMER_MODE_ATTEMPTS = 3

    def tearDown(self):
        self.mock_curl.reset()


    def test_hammer_mode(self):
        """
        Тест hammer_mod'a; Все запросы кроме последнего будут прерваны
        по таймауту
        """

        #сбрасываем счетчик запросов
        tinycurl.get('http://ttttest.lc/hammer_mode/%s/1' % str(tinycurl.HAMMER_MODE_ATTEMPTS-1))

        result = tinycurl.get('http://ttttest.lc/hammer_mode/%s/0' % str(tinycurl.HAMMER_MODE_ATTEMPTS-1))['body']

        self.assertEqual('test', result)

    def test_hammer_mode_with_proxy(self):
        """
        Тест hammer_mod'a; Все запросы кроме последнего будут прерваны
        по таймауту; Используем прокси
        """
        #сбрасываем счетчик запросов
        tinycurl.get('http://ttttest.lc/hammer_mode/%s/1' % str(tinycurl.HAMMER_MODE_ATTEMPTS-1), proxy='127.0.0.1:8766')

        result = tinycurl.get('http://ttttest.lc/hammer_mode/%s/0' % str(tinycurl.HAMMER_MODE_ATTEMPTS-1), proxy='127.0.0.1:8766')['body']

        self.assertEqual('test', result)

    def test_simple_load(self):
        """загружаем обычную страницу. Прокси НЕ используем"""
        result = tinycurl.get('http://ttttest.lc/test')['body']
        self.assertEqual('test_simple_load', result)

    def test_simple_load_with_proxy(self):
        """загружаем обычную страницу. Используем прокси"""
        result = tinycurl.get('http://ttttest.lc/test', proxy='127.0.0.1:8766')['body']
        self.assertEqual('test_simple_load', result)

    def test_load_with_redirect(self):
        """
        переходим по адресу с которого нас редиректит на страницу
        с контрольным текстом. БЕЗ прокси
        """
        result = tinycurl.get('http://ttttest.lc/redir')['body']
        self.assertEqual('redirect', result)

    def test_load_with_redirect_and_proxy(self):
        """
        переходим по адресу с которого нас редиректит на страницу
        с контрольным текстом. Используем прокси
        """
        result = tinycurl.get('http://ttttest.lc/redir', proxy='127.0.0.1:8766')['body']
        self.assertEqual('redirect', result)

    def test_simple_post(self):
        """Отправляем post запрос, в теле ответа будут посланные данные"""
        result = tinycurl.post('http://ttttest.lc/simple_post', 
                                data={'some_input': 'redirect'})['body']
        self.assertEqual('redirect', result)

    def test_simple_post_proxy(self):
        """ 
        Отправляем post запрос, в теле ответа будут посланные данные
        Используем прокси
        """
        result = tinycurl.post('http://ttttest.lc/simple_post', 
                                data={'some_input': 'redirect'},
                                proxy='127.0.0.1:8766')['body']
        self.assertEqual('redirect', result)

    def test_simple_cookies(self):
        """проверяем корректное получение установаленных куки"""
        result = tinycurl.get('http://ttttest.lc/cookies')['cookies']

        self.assertEqual('test_cookie=test', result)

    def test_simple_cookies_proxy(self):
        """проверяем корректное получение установаленных куки; С прокси"""
        result = tinycurl.get('http://ttttest.lc/cookies', 
                               proxy='127.0.0.1:8766')['cookies']

        self.assertEqual('test_cookie=test', result)

    def test_set_and_get_cookies(self):
        """
        Получаем куки и отдаём их в следующем запросе, в котором 
        значение кук должно быть в теле ответa
        """
        cookies = tinycurl.get('http://ttttest.lc/set_get_cookies')['cookies']
        result = tinycurl.get('http://ttttest.lc/set_get_cookies', cookies=cookies)['body']

        self.assertEqual('test', result)

    def test_set_and_get_cookies_proxy(self):
        """
        Получаем куки и отдаём их в следующем запросе, в котором 
        значение кук должно быть в теле ответa
        """
        cookies = tinycurl.get('http://ttttest.lc/set_get_cookies', 
                                proxy='127.0.0.1:8766')['cookies']

        result = tinycurl.get('http://ttttest.lc/set_get_cookies', 
                               proxy='127.0.0.1:8766', 
                               cookies=cookies)['body']

        self.assertEqual('test', result)

