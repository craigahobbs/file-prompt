# Licensed under the MIT License
# https://github.com/craigahobbs/ctxkit/blob/main/LICENSE

from contextlib import contextmanager
from io import StringIO
import json
import os
from tempfile import TemporaryDirectory
import unittest
import unittest.mock

import urllib3

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
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            main(['-g'])
        self.assertTrue(stdout.getvalue().startswith('# The ctxkit configuration file format'))
        self.assertEqual(stderr.getvalue(), '')


    def test_no_items(self):
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            with self.assertRaises(SystemExit) as cm_exc:
                main([])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertTrue(stderr.getvalue().endswith('ctxkit: error: no prompt items specified\n'))


    def test_message(self):
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            main(['-m', 'Hello', '-m', 'Goodbye'])
        self.assertEqual(stdout.getvalue(), '''\
Hello

Goodbye
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config(self):
        with create_test_files([
            ('test.json', json.dumps({
                'items': [
                    {'long': ['Hello,', 'message!']},
                    {'long': ['Hello,', 'long!']}
                ]
            }))
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            main(['-c', os.path.join(temp_dir, 'test.json')])
        self.assertEqual(stdout.getvalue(), '''\
Hello,
message!

Hello,
long!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config_first_outer(self):
        with create_test_files([
            ('test.json', json.dumps({
                'items': [
                    {'message': 'test1'},
                    {'config': 'test2.json'}
                ]
            })),
            ('test2.json', json.dumps({
                'items': [
                    {'long': ['test2']}
                ]
            }))
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            main(['-c', os.path.join(temp_dir, 'test.json')])
        self.assertEqual(stdout.getvalue(), '''\
test1

test2
''')
        self.assertEqual(stderr.getvalue(), '')



    def test_config_first_inner(self):
        with create_test_files([
            ('test.json', json.dumps({
                'items': [
                    {'config': 'test2.json'},
                    {'message': 'test1'}
                ]
            })),
            ('test2.json', json.dumps({
                'items': [
                    {'long': ['test2']}
                ]
            }))
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            main(['-c', os.path.join(temp_dir, 'test.json')])
        self.assertEqual(stdout.getvalue(), '''\
test2

test1
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config_failure(self):
        with unittest.mock.patch('ctxkit.main.POOL_MANAGER') as mock_pool_manager, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            # Create a mock Response object for the pull request
            mock_pull_response = unittest.mock.Mock(spec=urllib3.response.HTTPResponse)
            mock_pull_response.status = 500

            # Configure the mock PoolManager instance
            mock_pool_manager.request.return_value = mock_pull_response

            unknown_path = os.path.join('not-found', 'unknown.json')
            with self.assertRaises(SystemExit) as cm_exc:
                main(['-c', unknown_path, '-c', 'https://test.local/unknown.json'])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), f'''\
Error: [Errno 2] No such file or directory: {unknown_path!r}
''')


    def test_config_url(self):
        with unittest.mock.patch('ctxkit.main.POOL_MANAGER') as mock_pool_manager, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            # Create a mock Response object for the pull request
            mock_pull_response = unittest.mock.Mock(spec=urllib3.response.HTTPResponse)
            mock_pull_response.status = 200
            mock_pull_response.data = b'{"items": [{"message": "Hello!"}]}'

            # Configure the mock PoolManager instance
            mock_pool_manager.request.return_value = mock_pull_response

            main(['-c', 'https://invalid.local/test.json'])
        self.assertEqual(stdout.getvalue(), '''\
Hello!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_config_nested(self):
        with create_test_files([
            ('main.json', json.dumps({
                'items': [
                    {'config': os.path.join('subdir', 'nested.json')},
                    {'message': 'Main message'}
                ]
            })),
            (('subdir', 'nested.json'), json.dumps({
                'items': [
                    {'file': 'nested.txt'}
                ]
            })),
            (('subdir', 'nested.txt'), 'Nested message')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
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
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            with self.assertRaises(SystemExit) as cm_exc:
                main(['-c', os.path.join(temp_dir, 'invalid.json')])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '''\
Error: Unknown member 'items.0.invalid'
''')


    def test_include(self):
        with create_test_files([
            ('test.txt', 'Hello!'),
            ('test2.txt', 'Hello2!')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            file_path2 = os.path.join(temp_dir, 'test2.txt')
            main(['-i', file_path, '-i', file_path2])
        self.assertEqual(stdout.getvalue(), '''\
Hello!

Hello2!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_include_url(self):
        with unittest.mock.patch('ctxkit.main.POOL_MANAGER') as mock_pool_manager, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            # Create a mock Response object for the pull request
            mock_pull_response = unittest.mock.Mock(spec=urllib3.response.HTTPResponse)
            mock_pull_response.status = 200
            mock_pull_response.data = b'URL content\n'

            # Configure the mock PoolManager instance
            mock_pool_manager.request.return_value = mock_pull_response

            main(['-i', 'https://test.local'])
        self.assertEqual(stdout.getvalue(), '''\
URL content
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_include_variable(self):
        with create_test_files([
            ('test.txt', 'Hello!')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            file_path_var = os.path.join(temp_dir, '{{name}}.txt')
            main(['-v', 'name', 'test', '-i', file_path_var])
        self.assertEqual(stdout.getvalue(), '''\
Hello!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_include_empty(self):
        with create_test_files([
            ('test.txt', '')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-i', file_path])
        self.assertEqual(stdout.getvalue(), '\n')
        self.assertEqual(stderr.getvalue(), '')


    def test_include_strip(self):
        with create_test_files([
            ('test.txt', '\nHello!\n')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-i', file_path])
        self.assertEqual(stdout.getvalue(), '''\
Hello!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_include_error(self):
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            unknown_path = os.path.join('not-found', 'unknown.txt')
            with self.assertRaises(SystemExit) as cm_exc:
                main(['-i', unknown_path])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), f'''\
Error: [Errno 2] No such file or directory: '{unknown_path}'
''')


    def test_file(self):
        with create_test_files([
            ('test.txt', 'Hello!'),
            ('test2.txt', 'Hello2!')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
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


    def test_file_url(self):
        with unittest.mock.patch('ctxkit.main.POOL_MANAGER') as mock_pool_manager, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            # Create a mock Response object for the pull request
            mock_pull_response = unittest.mock.Mock(spec=urllib3.response.HTTPResponse)
            mock_pull_response.status = 200
            mock_pull_response.data = b'URL content\n'

            # Configure the mock PoolManager instance
            mock_pool_manager.request.return_value = mock_pull_response

            main(['-f', 'https://test.local'])
        self.assertEqual(stdout.getvalue(), '''\
<https://test.local>
URL content
</https://test.local>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_file_variable(self):
        with create_test_files([
            ('test.txt', 'Hello!')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            file_path_var = os.path.join(temp_dir, '{{name}}.txt')
            main(['-v', 'name', 'test', '-f', file_path_var])
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
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
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
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            file_path = os.path.join(temp_dir, 'test.txt')
            main(['-f', file_path])
        self.assertEqual(stdout.getvalue(), f'''\
<{file_path}>
Hello!
</{file_path}>
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_file_error(self):
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            unknown_path = os.path.join('not-found', 'unknown.txt')
            with self.assertRaises(SystemExit) as cm_exc:
                main(['-f', unknown_path])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), f'''\
Error: [Errno 2] No such file or directory: '{unknown_path}'
''')


    def test_dir(self):
        with create_test_files([
            ('test.txt', 'Hello!'),
            (('subdir', 'sub.txt'), 'Goodbye!')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
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


    def test_dir_variable(self):
        with create_test_files([
            (('subdir', 'sub.txt'), 'Goodbye!'),
            (('subdir2', 'sub2.txt'), 'Goodbye2!')
        ]) as temp_dir, \
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            sub_path = os.path.join(temp_dir, 'subdir', 'sub.txt')
            sub_dir_var = os.path.join(temp_dir, '{{name}}')
            main(['-v', 'name', 'subdir', '-d', sub_dir_var, '-x', 'txt'])
        self.assertEqual(stdout.getvalue(), f'''\
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
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
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
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
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
             unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            with self.assertRaises(SystemExit) as cm_exc:
                main(['-d', temp_dir, '-x', 'txt'])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), f'''\
Error: No files found, "{temp_dir}"
''')


    def test_dir_relative_not_found(self):
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            unknown_path = os.path.join('not-found', 'unknown')
            unknown_path2 = os.path.join('not-found', 'unknown2')
            with self.assertRaises(SystemExit) as cm_exc:
                main(['-d', unknown_path, '-d', unknown_path2, '-x', 'txt'])
        self.assertEqual(cm_exc.exception.code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), f'''\
Error: [Errno 2] No such file or directory: '{unknown_path}'
''')


    def test_variable(self):
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            main(['-v', 'first', 'Foo', '-v', 'Last', 'Bar', '-m', 'Hello, {{first}} {{ Last }}!'])
        self.assertEqual(stdout.getvalue(), '''\
Hello, Foo Bar!
''')
        self.assertEqual(stderr.getvalue(), '')


    def test_variable_unknown(self):
        with unittest.mock.patch('sys.stdout', StringIO()) as stdout, \
             unittest.mock.patch('sys.stderr', StringIO()) as stderr:
            main(['-v', 'Last', 'Bar', '-m', 'Hello, {{first}} {{ Last }}!'])
        self.assertEqual(stdout.getvalue(), '''\
Hello,  Bar!
''')
        self.assertEqual(stderr.getvalue(), '')
