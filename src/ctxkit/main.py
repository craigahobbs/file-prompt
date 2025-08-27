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
import urllib.request

import schema_markdown


def main(argv=None):
    """
    ctxkit command-line script main entry point
    """

    # Command line arguments
    parser = argparse.ArgumentParser(prog='ctxkit')
    parser.add_argument('-g', '--config-help', action='store_true',
                        help='display the ctxkit config file format')
    parser.add_argument('-c', '--config', metavar='PATH', dest='items', action=TypedItemAction,
                        help='include the ctxkit config')
    parser.add_argument('-m', '--message', metavar='TEXT', dest='items', action=TypedItemAction,
                        help='include the prompt message')
    parser.add_argument('-u', '--url', metavar='URL', dest='items', action=TypedItemAction,
                        help='include the URL')
    parser.add_argument('-f', '--file', metavar='PATH', dest='items', action=TypedItemAction,
                        help='include the file')
    parser.add_argument('-d', '--dir', metavar='PATH', dest='items', action=TypedItemAction,
                        help="include a directory's files")
    parser.add_argument('-x', '--ext', metavar='EXT', action='append', default=[],
                        help='include files with the extension')
    parser.add_argument('-l', '--depth', metavar='N', type=int, default=0,
                        help='the maximum directory depth, default is 0 (infinite)')
    parser.add_argument('-v', '--var', nargs=2, metavar=('VAR', 'EXPR'), dest='items', action=TypedItemAction,
                        help='define a variable (reference with "{{var}}")')
    args = parser.parse_args(args=argv)
    if args.config_help:
        parser.exit(message=CTXKIT_SMD)

    # Load the config file
    config = {'items': []}
    for item_type, item_value in (args.items or []):
        if item_type == 'c':
            config['items'].append({'config': item_value})
        elif item_type == 'f':
            config['items'].append({'file': item_value})
        elif item_type == 'd':
            config['items'].append({'dir': {'path': item_value, 'exts': args.ext, 'depth': args.depth}})
        elif item_type == 'u':
            config['items'].append({'url': item_value})
        elif item_type == 'v':
            config['items'].append({'var': {'name': item_value[0], 'value': item_value[1]}})
        else: # if item_type == 'm':
            config['items'].append({'message': item_value})

    # Validate the configuration
    if not config['items']:
        parser.error('no prompt items specified')
    config = schema_markdown.validate_type(CTXKIT_TYPES, 'CtxKitConfig', config)

    # Process the configuration
    _process_config(config, {})


def _process_config(config, variables, root_dir='.'):
    # Output the prompt items
    is_first = True
    for item in config['items']:
        item_key = list(item.keys())[0]

        # Config item
        if item_key == 'config':
            config_path = item['config']

            # Load the config path or URL
            config_error = None
            try:
                if re.match(_R_URL, config_path):
                    with urllib.request.urlopen(config_path) as config_response:
                        config_text = config_response.read().decode('utf-8')
                else:
                    if not os.path.isabs(config_path):
                        config_path = os.path.normpath(os.path.join(root_dir, config_path))
                    with open(config_path, 'r', encoding='utf-8') as config_file:
                        config_text = config_file.read()
                config = json.loads(config_text)
            except Exception as exc:
                config = None
                config_error = str(exc)

            # Process the config file
            if config is None:
                if not is_first:
                    print()
                print(f'Error: Failed to load configuration file, "{config_path}", with error: {config_error}')
            else:
                # Validate the configuration
                config = schema_markdown.validate_type(CTXKIT_TYPES, 'CtxKitConfig', config)

                # Process the configuration
                _process_config(config, variables, os.path.dirname(config_path))

        # File item
        elif item_key == 'file':
            file_path = _replace_variables(item['file'], variables)
            if not os.path.isabs(file_path):
                file_path = os.path.normpath(os.path.join(root_dir, file_path))

            # Read the file
            try:
                with open(file_path, 'r', encoding='utf-8') as file_file:
                    file_text = file_file.read().strip()
            except:
                file_text = f'Error: File not found, "{file_path}"'

            # Output the file
            if not is_first:
                print()
            print(f'<{file_path}>')
            if file_text:
                print(file_text)
            print(f'</{file_path}>')

        # Directory item
        elif item_key == 'dir':
            # Recursively find the files of the requested extensions
            dir_path = _replace_variables(item['dir']['path'], variables)
            if not os.path.isabs(dir_path):
                dir_path = os.path.normpath(os.path.join(root_dir, dir_path))
            dir_exts = [f'.{ext.lstrip(".")}' for ext in item['dir'].get('exts') or []]
            dir_depth = item['dir'].get('depth', 0)
            try:
                dir_files = list(_get_directory_files(dir_path, dir_exts, dir_depth))
            except:
                dir_files = []

            # Output the file text
            if not dir_files:
                if not is_first:
                    print()
                print(f'Error: No files found, "{dir_path}"')
            else:
                for ix_file, file_path in enumerate(dir_files):
                    if not is_first or ix_file != 0:
                        print()
                    print(f'<{file_path}>')
                    with open(file_path, 'r', encoding='utf-8') as file_file:
                        file_text = file_file.read().strip()
                    if file_text:
                        print(file_text)
                    print(f'</{file_path}>')

        # URL item
        elif item_key == 'url':
            # Get the URL resource text
            url = _replace_variables(item['url'], variables)
            try:
                with urllib.request.urlopen(item['url']) as response:
                    url_text = response.read().strip().decode('utf-8')
            except:
                url_text = f'Error: Failed to fetch URL, "{url}"'

            # Output the URL resource text
            if not is_first:
                print()
            print(f'<{url}>')
            if url_text:
                print(url_text)
            print(f'</{url}>')

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


# Regular expression to match a URL
_R_URL = re.compile(r'^[a-z]+:')


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

    # Config file include
    string config

    # A prompt message
    string message

    # A long prompt message
    string[len > 0] long

    # File include path
    string file

    # Directory include
    CtxKitDir dir

    # URL include
    string url

    # Set a variable (reference with "{{var}}")
    CtxKitVariable var


# A directory include item
struct CtxKitDir

    # The directory path
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
