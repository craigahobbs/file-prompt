# Licensed under the MIT License
# https://github.com/craigahobbs/ctxkit/blob/main/LICENSE

from contextlib import contextmanager
from io import StringIO
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import schema_markdown

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
        {"long": ["Hello,", "message!"]},
        {"long": ["Hello,", "long!"]}
    ]
}
''')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-c', os.path.join(temp_dir, 'test.json')])
        self.assertEqual(stdout.getvalue(), '''\
Hello,
message!

Hello,
long!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config_failure(self):
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            mock_urlopen.side_effect = Exception('Boom!')
            main(['-c', 'not-found/unknown.json', '-c', 'https://test.local/unknown.json'])
        self.assertEqual(stdout.getvalue(), '''\
Error: Failed to load configuration file, "not-found/unknown.json"

Error: Failed to load configuration file, "https://test.local/unknown.json"
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config_url(self):
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            mock_response = unittest.mock.MagicMock()
            mock_response.read.return_value = b'{"items": [{"message": "Hello!"}]}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            main(['-c', 'https://invalid.local/test.json'])
        self.assertEqual(stdout.getvalue(), '''\
Hello!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config_nested(self):
        with create_test_files([
            ('main.json', f'''\
{{
    "items": [
        {{"config": "{os.path.join('subdir', 'nested.json')}"}},
        {{"message": "Main message"}}
    ]
}}
'''),
            (('subdir', 'nested.json'), '''\
{
    "items": [
        {"file": "nested.txt"}
    ]
}
'''),
            (('subdir', 'nested.txt'), 'Nested message')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            nested_path = os.path.join(temp_dir, 'subdir', 'nested.txt')
            main(['-c', os.path.join(temp_dir, 'main.json')])
        self.assertEqual(stdout.getvalue(), f'''\
<{nested_path}>
Nested message
</{nested_path}>

Main message
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config_invalid(self):
        with create_test_files([
            ('invalid.json', '{"items": [{"invalid": "value"}]}')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            with self.assertRaises(schema_markdown.ValidationError) as cm_exc:
                main(['-c', os.path.join(temp_dir, 'invalid.json')])
        self.assertEqual(str(cm_exc.exception), "Unknown member 'items.0.invalid'")
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')


    def test_file(self):
        with create_test_files([
            ('test.txt', 'Hello!'),
            ('test2.txt', 'Hello2!')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            file_path2 = os.path.join(temp_dir, 'test2.txt')
            main(['-f', file_path, '-f', file_path2])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
Hello!
</{file_path}>

<{file_path2}>
Hello2!
</{file_path2}>
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


    def test_file_relative_not_found(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-f', 'not-found/unknown.txt'])
        self.assertEqual(stdout.getvalue(), '''\
<not-found/unknown.txt>
Error: File not found, "not-found/unknown.txt"
</not-found/unknown.txt>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_url(self):
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            mock_response = unittest.mock.MagicMock()
            mock_response.read.return_value = b'URL content\n'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            main(['-u', 'https://test.local'])
        self.assertEqual(stdout.getvalue(), '''\
<https://test.local>
URL content
</https://test.local>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_url_second(self):
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            mock_response = unittest.mock.MagicMock()
            mock_response.read.return_value = b'URL content\n'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            main(['-m', 'Hello!', '-u', 'https://test.local'])
        self.assertEqual(stdout.getvalue(), '''\
Hello!

<https://test.local>
URL content
</https://test.local>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_url_empty(self):
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            mock_response = unittest.mock.MagicMock()
            mock_response.read.return_value = b''
            mock_urlopen.return_value.__enter__.return_value = mock_response
            main(['-u', 'https://test.local'])
        self.assertEqual(stdout.getvalue(), '''\
<https://test.local>
</https://test.local>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_url_exception(self):
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            mock_urlopen.side_effect = Exception('Boom!')
            main(['-u', 'https://invalid.local'])
        self.assertEqual(stdout.getvalue(), '''\
<https://invalid.local>
Error: Failed to fetch URL, "https://invalid.local"
</https://invalid.local>
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


    def test_dir_depth(self):
        with create_test_files([
            ('test.txt', 'Hello!'),
            (('subdir', 'sub.txt'), 'Goodbye!')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-d', temp_dir, '-x', 'txt', '-l', '1'])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
Hello!
</{file_path}>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_dir_empty(self):
        with create_test_files([
            ('test.txt', '')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-d', temp_dir, '-x', 'txt'])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
</{file_path}>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_dir_no_files(self):
        with create_test_files([
            (('subdir', 'file1.md'), 'Content1')
        ]) as temp_dir, \
             patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-d', temp_dir, '-x', 'txt'])
        self.assertEqual(stdout.getvalue(), f'''\
Error: No files found, "{temp_dir}"
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_dir_relative_not_found(self):
        with patch('sys.stdout', StringIO()) as stdout, \
             patch('sys.stderr', StringIO()) as stderr:
            main(['-d', 'not-found/unknown/', '-d', 'not-found/unknown2', '-x', 'txt'])
        self.assertEqual(stdout.getvalue(), '''\
Error: No files found, "not-found/unknown"

Error: No files found, "not-found/unknown2"
''')
        self.assertEqual(stderr.getvalue(), '')
