# Licensed under the MIT License
# https://github.com/craigahobbs/ctxkit/blob/main/LICENSE

from contextlib import contextmanager
from io import StringIO
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import ctxkit.__main__
from ctxkit.main import main


# Helper context manager to create a list of files in a temporary directory
@contextmanager
def create_test_files(file_defs):
    tempdir = TemporaryDirectory()
    try:
        for path_parts, content in file_defs:
            if isinstance(path_parts, str):
                path_parts = [path_parts]
            path = os.path.join(tempdir.name, *path_parts)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as file_:
                file_.write(content)
        yield tempdir.name
    finally:
        tempdir.cleanup()


class TestMain(unittest.TestCase):

    def test_main_submodule(self):
        self.assertTrue(ctxkit.__main__)


    def test_help_config(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            with self.assertRaises(SystemExit) as cm_exc:
                main(['-g'])
        self.assertEqual(cm_exc.exception.code, 0)
        self.assertEqual(stdout.getvalue(), '')
        self.assertTrue(stderr.getvalue().startswith('# The ctxkit configuration file format'))


    def test_no_items(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            with self.assertRaises(SystemExit) as cm_exc:
                main([])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertTrue(stderr.getvalue().endswith('ctxkit: error: no prompt items specified\n'))


    def test_message(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-m', 'Hello', '-m', 'Goodbye'])
        self.assertEqual(stdout.getvalue(), '''\
Hello

Goodbye
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config(self):
        with create_test_files([
            ('test.json', '''\
{
    "items": [
        {"message": "Hello, message!"},
        {"long": ["Hello,", "long!"]}
    ]
}
'''), \
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-c', os.path.join(temp_dir, 'test.json')])
        self.assertEqual(stdout.getvalue(), '''\
Hello, message!

Hello,
long!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_file(self):
        with create_test_files([
            ('test.txt', 'Hello!')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-f', file_path])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
Hello!
</{file_path}>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_file_empty(self):
        with create_test_files([
            ('test.txt', '')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-f', file_path])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
</{file_path}>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_file_strip(self):
        with create_test_files([
            ('test.txt', '\nHello!\n')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-f', file_path])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
Hello!
</{file_path}>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_url(self):
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            mock_response = unittest.mock.MagicMock()
            mock_response.read.return_value = b'URL content\n'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            main(['-u', 'http://test.local'])
        self.assertEqual(stdout.getvalue(), '''\
<http://test.local>
URL content
</http://test.local>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_dir(self):
        with create_test_files([
            ('test.txt', 'Hello!'),
            (('subdir', 'sub.txt'), 'Goodbye!')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            sub_path = os.path.join(temp_dir, 'subdir', 'sub.txt')
            main(['-d', temp_dir, '-x', 'txt'])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
Hello!
</{file_path}>
<{sub_path}>
Goodbye!
</{sub_path}>
''')
        self.assertEqual(stderr.getvalue(), '')
