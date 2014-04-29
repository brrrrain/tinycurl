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
        tinycurl.HEADERS = []
        tinycurl.USERAGENT = ''


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

    def test_global_header(self):
        """Устанавливаем глобальное значение хедеров"""
        tinycurl.HEADERS = ['Test-header: test']
        result = tinycurl.get('http://ttttest.lc/header')['body']

        self.assertEqual('test', result)

    def test_passed_header(self):
        """Передаём значения хедеров"""
        result = tinycurl.get('http://ttttest.lc/header',
                              headers=['Test-header: test'])['body']
        self.assertEqual('test', result)

    def test_passed_header_with_redirect(self):
        """Передаём значения хедеров, но нас редиректит"""
        result = tinycurl.get('http://ttttest.lc/redirect_to_header', 
                              headers=['Test-header: test'])['body']
        self.assertEqual('test', result)

    def test_global_header_with_redirect(self):
        """Глобальное значение хедеров, но нас редиректит"""
        tinycurl.HEADERS = ['Test-header: test']
        result = tinycurl.get('http://ttttest.lc/redirect_to_header')['body']
        self.assertEqual('test', result)

    def test_passed_header_post(self):
        """Передаём значения хедеров; POST запрос"""
        result = tinycurl.post('http://ttttest.lc/header', data={'a': 'b'},
                                headers=['Test-header: test'])['body']
        self.assertEqual('test', result)

    def test_passed_header_with_redirect_post(self):
        """Передаём значения хедеров, но нас редиректит; POST запрос"""
        result = tinycurl.post('http://ttttest.lc/redirect_to_header', 
                               data={'a': 'b'},
                               headers=['Test-header: test'])['body']
        self.assertEqual('test', result)

    def test_passed_header_with_redirect_post(self):
        """Глобальное значение хедеров, но нас редиректит; POST запрос"""
        tinycurl.HEADERS = ['Test-header: test']
        result = tinycurl.post('http://ttttest.lc/redirect_to_header', 
                               data={'a': 'b'})['body']
        self.assertEqual('test', result)

    def test_global_useragent(self):
        """глобальное значение User-agent"""
        tinycurl.USERAGENT = 'test-useragent'
        result = tinycurl.get('http://ttttest.lc/useragent')['body']

        self.assertEqual('test-useragent', result)

    def test_passed_useragent(self):
        """Переданое значение User-agent"""
        result = tinycurl.get('http://ttttest.lc/useragent', useragent='test-useragent')['body']

        self.assertEqual('test-useragent', result)

    def test_global_useragent_post(self):
        """глобальное значение User-agent; POST запрос"""
        tinycurl.USERAGENT = 'test-useragent'
        result = tinycurl.post('http://ttttest.lc/useragent',
                               data={'a': 'b'})['body']

        self.assertEqual('test-useragent', result)

    def test_passed_useragent_post(self):
        """Переданое значение User-agent; POST запрос"""
        result = tinycurl.post('http://ttttest.lc/useragent',
                               data={'a': 'b'},
                               useragent='test-useragent')['body']

        self.assertEqual('test-useragent', result)

    def test_passed_useragent_with_redirect(self):
        """Переданое значение User-agent; Редиректит"""
        result = tinycurl.get('http://ttttest.lc/redirect_to_useragent', 
                              useragent='test-useragent')['body']

        self.assertEqual('test-useragent', result)

    def test_global_useragent_with_redirect(self):
        """Глобальное значение User-agent; Редиректит"""
        tinycurl.USERAGENT = 'test-useragent'
        result = tinycurl.get('http://ttttest.lc/redirect_to_useragent')['body']

        self.assertEqual('test-useragent', result)

    def test_passed_useragent_with_redirect_post(self):
        """Переданое значение User-agent; Редиректит; POST запрос"""
        result = tinycurl.post('http://ttttest.lc/redirect_to_useragent', 
                               data={'a': 'b'},
                               useragent='test-useragent')['body']

        self.assertEqual('test-useragent', result)

    def test_global_useragent_with_redirect_post(self):
        """Глобальное значение User-agent; Редиректит; POST запрос"""
        tinycurl.USERAGENT = 'test-useragent'
        result = tinycurl.post('http://ttttest.lc/redirect_to_useragent', 
                               data={'a': 'b'})['body']

        self.assertEqual('test-useragent', result)
