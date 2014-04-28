#encoding: utf-8

import unittest
import logging
import pycurl
import tinycurl
from tinycurl_exceptions import DeadProxy, WrongCode, InfiniteRedirection
import curlpretty
import controllers

class TestExceptions(unittest.TestCase):
    def test_connect_error_without_proxy_and_bad_host(self):
        """Прокси НЕ используется, хост НЕ существует."""
        self.assertRaises(pycurl.error, tinycurl.get, 'http://fsd5sd5fs5f.lc')

    def test_connect_error_without_proxy_and_bad_code(self):
        """Прокси НЕ используется, хост существует, но отдаёт код >=400"""
        self.assertRaises(WrongCode, tinycurl.get, 'http://yandex.ru/404_page!')

    def test_connect_error_with_good_proxy_and_bad_host(self):
        """Прокси РАБОЧИЙ, хост НЕ существует"""
        self.assertRaises(DeadProxy, tinycurl.get, 'http://fsd5sd5fs5f.lc', proxy='127.0.0.1:9999')

    def test_connect_error_with_bad_proxy_and_good_host(self):
        """Прокси НЕрабочий, хост НЕ существует"""
        self.assertRaises(DeadProxy, tinycurl.get, 'http://yandex.ru', proxy='127.0.0.2:9999')

    def test_connect_error_with_good_proxy_and_bad_code(self):
        """Прокси РАБОЧИЙ, хост существует, но отдаёт код >=400"""
        self.assertRaises(WrongCode, tinycurl.get, 'http://yandex.ru/404_page!', proxy='127.0.0.1:9999')

    def test_looping_error(self):
        m = curlpretty.curlpretty(controllers)
        m.mock()
        """Прокси РАБОЧИЙ, хост существует, но отдаёт код >=400"""
        self.assertRaises(InfiniteRedirection, tinycurl.get, 'http://test.lc/looping')
        m.reset()
