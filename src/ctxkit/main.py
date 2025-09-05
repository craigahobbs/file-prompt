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

import schema_markdown
import urllib3

from .grok import POOL_MANAGER, grok_chat


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
    parser.add_argument('--grok', metavar='MODEL',
                        help='pass stdin to the Grok API')
    parser.add_argument('--temp', metavar='TEMP', type=float, default=0.7,
                        help='the LLM temperature (default is 0.7)')
    args = parser.parse_args(args=argv)

    # Show configuration file format?
    if args.config_help:
        print(CTXKIT_SMD.strip())
        return

    # Grok chat?
    if args.grok:
        for chunk in grok_chat(args.grok, sys.stdin.read(), temperature=args.temp):
            print(chunk, end='', flush=True)
        print()
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
        for ix_item, item_text in enumerate(process_config_items(config, {})):
            if ix_item != 0:
                print()
            print(item_text)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(2)


def process_config(config, variables, root_dir='.'):
    return '\n\n'.join(process_config_items(config, variables, root_dir))


def process_config_items(config, variables, root_dir='.'):
    # Output the prompt items
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
            yield from process_config_items(config, variables, os.path.dirname(item_path))

        # File include item
        elif item_key == 'include':
            yield _fetch_text(item_path)

        # File item
        elif item_key == 'file':
            file_text = _fetch_text(item_path)
            yield f'<{item_path}>\n{file_text}{"\n" if file_text else ""}</{item_path}>'


        # Directory item
        elif item_key == 'dir':
            # Recursively find the files of the requested extensions
            dir_exts = [f'.{ext.lstrip(".")}' for ext in item['dir'].get('exts') or []]
            dir_depth = item['dir'].get('depth', 0)
            dir_files = list(_get_directory_files(item_path, dir_exts, dir_depth))
            if not dir_files:
                raise Exception(f'No files found, "{item_path}"')

            # Output the file text
            for file_path in dir_files:
                file_text = _fetch_text(file_path)
                yield f'<{file_path}>\n{file_text}{"\n" if file_text else ""}</{file_path}>'

        # Variable definition item
        elif item_key == 'var':
            variables[item['var']['name']] = item['var']['value']

        # Long message item
        elif item_key == 'long':
            yield _replace_variables('\n'.join(item['long']), variables)

        # Message item
        else: # if item_key == 'message'
            yield _replace_variables(item['message'], variables)


# Helper to determine if a path is a URL
def _is_url(path):
    return re.match(_R_URL, path)

_R_URL = re.compile(r'^[a-z]+:')


# Helper to fetch a file or URL text
def _fetch_text(path):
    if _is_url(path):
        response = POOL_MANAGER.request(method='GET', url=path, retries=0)
        try:
            if response.status != 200:
                raise urllib3.exceptions.HTTPError(f'POST {path} failed with status {response.status}')
            return response.data.decode('utf-8').strip()
        finally:
            response.close()
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
