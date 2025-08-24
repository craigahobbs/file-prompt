# Licensed under the MIT License
# https://github.com/craigahobbs/promptkit/blob/main/LICENSE

from io import StringIO
import unittest
from unittest.mock import patch

import promptkit.__main__
from promptkit.main import main


class TestMain(unittest.TestCase):

    def test_main_submodule(self):
        self.assertTrue(promptkit.__main__)


    def test_main(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-m', 'Hello', '-m', 'Goodbye'])
        self.assertEqual(stdout.getvalue(), '''\
Hello

Goodbye
''')
        self.assertEqual(stderr.getvalue(), '')
