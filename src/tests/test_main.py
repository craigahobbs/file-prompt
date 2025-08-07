# Licensed under the MIT License
# https://github.com/craigahobbs/file-prompt/blob/main/LICENSE

from io import StringIO
import unittest
from unittest.mock import patch

import file_prompt.__main__
from file_prompt.main import main


class TestMain(unittest.TestCase):

    def test_main_submodule(self):
        self.assertTrue(file_prompt.__main__)


    def test_main(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-m', 'Hello', '-m', 'Goodbye'])
        self.assertEqual(stdout.getvalue(), '''\
Hello

Goodbye
''')
        self.assertEqual(stderr.getvalue(), '')
