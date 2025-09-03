# Licensed under the MIT License
# https://github.com/craigahobbs/ctxkit/blob/main/LICENSE

"""
ctxkit command-line script main module
"""

import argparse
from functools import partial
import json
import os
import re
import sys
import urllib.request

import schema_markdown


def main(argv=None):
    """
    ctxkit command-line script main entry point
    """

    # Command line arguments
    parser = argparse.ArgumentParser(prog='ctxkit')
    parser.add_argument('-g', '--config-help', action='store_true',
                        help='display the JSON configuration file format')
    parser.add_argument('-c', '--config', metavar='PATH', dest='items', action=TypedItemAction,
                        help='process the JSON configuration file path or URL')
    parser.add_argument('-m', '--message', metavar='TEXT', dest='items', action=TypedItemAction,
                        help='add a prompt message')
    parser.add_argument('-i', '--include', metavar='PATH', dest='items', action=TypedItemAction,
                        help='add the file path or URL text')
    parser.add_argument('-f', '--file', metavar='PATH', dest='items', action=TypedItemAction,
                        help='add the file path or URL as a text file')
    parser.add_argument('-d', '--dir', metavar='PATH', dest='items', action=TypedItemAction,
                        help="add a directory's text files")
    parser.add_argument('-x', '--ext', metavar='EXT', action='append', default=[],
                        help='add a directory text file extension')
    parser.add_argument('-l', '--depth', metavar='N', type=int, default=0,
                        help='the maximum directory depth, default is 0 (infinite)')
    parser.add_argument('-v', '--var', nargs=2, metavar=('VAR', 'EXPR'), dest='items', action=TypedItemAction,
                        help='define a variable (reference with "{{var}}")')
    args = parser.parse_args(args=argv)

    # Show configuration file format?
    if args.config_help:
        print(CTXKIT_SMD.strip())
        return

    # Load the config file
    config = {'items': []}
    for item_type, item_value in (args.items or []):
        if item_type == 'c':
            config['items'].append({'config': item_value})
        elif item_type == 'i':
            config['items'].append({'include': item_value})
        elif item_type == 'f':
            config['items'].append({'file': item_value})
        elif item_type == 'd':
            config['items'].append({'dir': {'path': item_value, 'exts': args.ext, 'depth': args.depth}})
        elif item_type == 'v':
            config['items'].append({'var': {'name': item_value[0], 'value': item_value[1]}})
        else: # if item_type == 'm':
            config['items'].append({'message': item_value})

    # Validate the configuration
    if not config['items']:
        parser.error('no prompt items specified')
    config = schema_markdown.validate_type(CTXKIT_TYPES, 'CtxKitConfig', config)

    # Process the configuration
    try:
        _process_config(config, {})
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(2)


def _process_config(config, variables, root_dir='.'):
    # Output the prompt items
    is_first = True
    for item in config['items']:
        item_key = list(item.keys())[0]

        # Get the item path, if any
        item_path = None
        if item_key in ('config', 'include', 'file'):
            item_path = _replace_variables(item[item_key], variables)
        elif item_key == 'dir':
            item_path = _replace_variables(item[item_key]['path'], variables)

        # Normalize the item path
        if item_path is not None and not _is_url(item_path) and not os.path.isabs(item_path):
            item_path = os.path.normpath(os.path.join(root_dir, item_path))

        # Config item
        if item_key == 'config':
            config = schema_markdown.validate_type(CTXKIT_TYPES, 'CtxKitConfig', json.loads(_fetch_text(item_path)))
            _process_config(config, variables, os.path.dirname(item_path))

        # File include item
        elif item_key == 'include':
            if not is_first:
                print()
            print(_fetch_text(item_path))

        # File item
        elif item_key == 'file':
            if not is_first:
                print()
            file_text = _fetch_text(item_path)
            print(f'<{item_path}>')
            if file_text:
                print(file_text)
            print(f'</{item_path}>')

        # Directory item
        elif item_key == 'dir':
            # Recursively find the files of the requested extensions
            dir_exts = [f'.{ext.lstrip(".")}' for ext in item['dir'].get('exts') or []]
            dir_depth = item['dir'].get('depth', 0)
            dir_files = list(_get_directory_files(item_path, dir_exts, dir_depth))
            if not dir_files:
                raise Exception(f'No files found, "{item_path}"')

            # Output the file text
            for ix_file, file_path in enumerate(dir_files):
                if not is_first or ix_file != 0:
                    print()
                file_text = _fetch_text(file_path)
                print(f'<{file_path}>')
                if file_text:
                    print(file_text)
                print(f'</{file_path}>')

        # Variable definition item
        elif item_key == 'var':
            variables[item['var']['name']] = item['var']['value']

        # Long message item
        elif item_key == 'long':
            if not is_first:
                print()
            for message in item['long']:
                print(_replace_variables(message, variables))

        # Message item
        else: # if item_key == 'message'
            if not is_first:
                print()
            print(_replace_variables(item['message'], variables))

        # Set not first
        if is_first and item_key != 'var':
            is_first = False


# Helper to determine if a path is a URL
def _is_url(path):
    return re.match(_R_URL, path)

_R_URL = re.compile(r'^[a-z]+:')


# Helper to fetch a file or URL text
def _fetch_text(path):
    if _is_url(path):
        with urllib.request.urlopen(path) as response:
            return response.read().decode('utf-8').strip()
    else:
        with open(path, 'r', encoding='utf-8') as file:
            return file.read().strip()


# Prompt item argument type
class TypedItemAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # Initialize the destination list if it doesn't exist
        if not hasattr(namespace, self.dest) or getattr(namespace, self.dest) is None:
            setattr(namespace, self.dest, [])

        # Get type_id from the option string (e.g., '-p' -> 'p')
        type_id = option_string.lstrip('-')[:1]

        # Append tuple (type_id, value)
        getattr(namespace, self.dest).append((type_id, values))


# Helper to replace variable references
def _replace_variables(text, variables):
    return _R_VARIABLE.sub(partial(_replace_variables_match, variables), text)

def _replace_variables_match(variables, match):
    var_name = match.group(1)
    return str(variables.get(var_name, ''))

_R_VARIABLE = re.compile(r'\{\{\s*([_a-zA-Z]\w*)\s*\}\}')


# Helper enumerator to recursively get a directory's files
def _get_directory_files(dir_name, file_exts, max_depth=0, current_depth=0):
    yield from (file_path for _, file_path in sorted(_get_directory_files_helper(dir_name, file_exts, max_depth, current_depth)))

def _get_directory_files_helper(dir_name, file_exts, max_depth, current_depth):
    # Recursion too deep?
    if max_depth > 0 and current_depth >= max_depth:
        return

    # Scan the directory for files
    for entry in os.scandir(dir_name):
        if entry.is_file():
            if os.path.splitext(entry.name)[1] in file_exts:
                file_path = os.path.normpath(os.path.join(dir_name, entry.name))
                yield (os.path.split(file_path), file_path)
        elif entry.is_dir(): # pragma: no branch
            dir_path = os.path.join(dir_name, entry.name)
            yield from _get_directory_files_helper(dir_path, file_exts, max_depth, current_depth + 1)


# The ctxkit configuration file format
CTXKIT_SMD = '''\
# The ctxkit configuration file format
struct CtxKitConfig

    # The list of prompt items
    CtxKitItem[len > 0] items


# A prompt item
union CtxKitItem

    # Config file path or URL
    string config

    # A prompt message
    string message

    # A long prompt message
    string[len > 0] long

    # File path or URL text
    string include

    # File path or URL as a text file
    string file

    # Add a directory's text files
    CtxKitDir dir

    # Set a variable (reference with "{{var}}")
    CtxKitVariable var


# A directory item
struct CtxKitDir

    # The directory file path or URL
    string path

    # The file extensions to include (e.g. ".py")
    string[] exts

    # The directory traversal depth (default is 0, infinite)
    optional int(>= 0) depth


# A variable definition item
struct CtxKitVariable

    # The variable's name
    string name

    # The variable's value
    string value
'''
CTXKIT_TYPES = schema_markdown.parse_schema_markdown(CTXKIT_SMD)
