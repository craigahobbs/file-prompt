# Licensed under the MIT License
# https://github.com/craigahobbs/promptmaker/blob/main/LICENSE

from io import StringIO
import unittest
from unittest.mock import patch

import promptmaker.__main__
from promptmaker.main import main


class TestMain(unittest.TestCase):

    def test_main_submodule(self):
        self.assertTrue(promptmaker.__main__)


    def test_main(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-m', 'Hello', '-m', 'Goodbye'])
        self.assertEqual(stdout.getvalue(), '''\
Hello

Goodbye
''')
        self.assertEqual(stderr.getvalue(), '')
