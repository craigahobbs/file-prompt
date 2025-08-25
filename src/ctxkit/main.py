# Licensed under the MIT License
# https://github.com/craigahobbs/ctxkit/blob/main/LICENSE

"""
ctxkit command-line script main module
"""

import argparse
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
    args = parser.parse_args(args=argv)
    if args.config_help:
        parser.exit(message=CTXKIT_SMD)

    # Load the config file
    config = {'items': []}
    for item_type, item_str in (args.items or []):
        if item_type == 'c':
            config['items'].append({'config': item_str})
        elif item_type == 'f':
            config['items'].append({'file': item_str})
        elif item_type == 'd':
            config['items'].append({'dir': {'path': item_str, 'exts': args.ext, 'depth': args.depth}})
        elif item_type == 'u':
            config['items'].append({'url': item_str})
        else: # if item_type == 'm':
            config['items'].append({'message': item_str})

    # Validate the configuration
    if not config['items']:
        parser.error('no prompt items specified')
    config = schema_markdown.validate_type(CTXKIT_TYPES, 'CtxKitConfig', config)

    # Process the configuration
    _process_config(config)


def _process_config(config, root_dir='.'):
    # Output the prompt items
    for ix_item, item in enumerate(config['items']):
        # Config item
        if 'config' in item:
            config_path = item['config']

            # Load the config path or URL
            if re.match(_R_URL, config_path):
                with urllib.request.urlopen(config_path) as config_response:
                    config_text = config_response.read().decode('utf-8')
            else:
                if not os.path.isabs(config_path):
                    config_path = os.path.normpath(os.path.join(root_dir, config_path))
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    config_text = config_file.read()
            config = json.loads(config_text)

            # Validate the configuration
            config = schema_markdown.validate_type(CTXKIT_TYPES, 'CtxKitConfig', config)

            # Process the configuration
            _process_config(config, os.path.dirname(config_path))

        # File item
        elif 'file' in item:
            file_path = item['file']
            if not os.path.isabs(file_path):
                file_path = os.path.normpath(os.path.join(root_dir, file_path))

            # Read the file
            try:
                with open(file_path, 'r', encoding='utf-8') as file_file:
                    file_text = file_file.read().strip()
            except:
                file_text = f'Error: File not found, "{file_path}"'

            # Output the file
            if ix_item != 0:
                print()
            print(f'<{file_path}>')
            if file_text:
                print(file_text)
            print(f'</{file_path}>')

        # Directory item
        elif 'dir' in item:
            dir_path = item['dir']['path']
            if not os.path.isabs(dir_path):
                dir_path = os.path.normpath(os.path.join(root_dir, dir_path))
            dir_exts = [f'.{ext.lstrip(".")}' for ext in item['dir'].get('exts') or []]
            dir_depth = item['dir'].get('depth', 0)
            for ix_file, file_path in enumerate(_get_directory_files(dir_path, dir_exts, dir_depth)):
                if ix_item != 0 or ix_file != 0:
                    print()
                print(f'<{file_path}>')
                with open(file_path, 'r', encoding='utf-8') as file_file:
                    file_text = file_file.read().strip()
                if file_text:
                    print(file_text)
                print(f'</{file_path}>')

        # URL item
        elif 'url' in item:
            # Get the URL resource text
            url = item['url']
            try:
                with urllib.request.urlopen(item['url']) as response:
                    url_text = response.read().strip().decode('utf-8')
            except:
                url_text = f'Error: Failed to fetch URL, "{url}"'

            # Output the URL resource text
            if ix_item != 0:
                print()
            print(f'<{url}>')
            if url_text:
                print(url_text)
            print(f'</{url}>')

        # Long message item
        elif 'long' in item:
            if ix_item != 0:
                print()
            for message in item['long']:
                print(message)

        # Message item
        else: # if 'message' in item:
            if ix_item != 0:
                print()
            print(item['message'])


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


# Helper enumerator to recursively get a directory's files
def _get_directory_files(dir_name, file_exts, max_depth=0, current_depth=0):
    yield from (file_path for _, file_path in sorted(_get_directory_files_helper(dir_name, file_exts, max_depth, current_depth)))

def _get_directory_files_helper(dir_name, file_exts, max_depth, current_depth):
    # Recursion too deep?
    if max_depth > 0 and current_depth > max_depth:
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


# A directory include item
struct CtxKitDir

    # The directory path
    string path

    # The file extensions to include (e.g. ".py")
    string[len >= 0] exts

    # The directory traversal depth (default is 0, infinite)
    optional int(>= 0) depth
'''
CTXKIT_TYPES = schema_markdown.parse_schema_markdown(CTXKIT_SMD)
