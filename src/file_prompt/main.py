# Licensed under the MIT License
# https://github.com/craigahobbs/file-prompt/blob/main/LICENSE

"""
file-prompt command-line script main module
"""

import argparse
import json
import os
import urllib.request

import schema_markdown


def main(argv=None):
    """
    file-prompt command-line script main entry point
    """

    # Command line arguments
    parser = argparse.ArgumentParser(prog='file-prompt')
    parser.add_argument('-g', '--config-help', action='store_true',
                        help='display the file-prompt config file format')
    parser.add_argument('-c', '--config', metavar='PATH', dest='items', action=TypedItemAction,
                        help='include the file-prompt config')
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
                        help='the maximum directory depth (default is 0)')
    args = parser.parse_args(args=argv)
    if args.config_help:
        parser.exit(status=2, message=FILE_PROMPT_SMD)

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
    schema_markdown.validate_type(FILE_PROMPT_TYPES, 'FilePromptConfig', config)

    # Process the configuration
    _process_config(config)


def _process_config(config):
    # Output the prompt items
    for ix_item, item in enumerate(config['items']):

        # Config item
        if 'config' in item:
            with open(item['config'], 'r', encoding='utf-8') as config_file:
                config = json.load(config_file)
            schema_markdown.validate_type(FILE_PROMPT_TYPES, 'FilePromptConfig', config)
            _process_config(config)

        # File item
        elif 'file' in item:
            file_path = item['file']
            if ix_item != 0:
                print()
            print(f'<{file_path}>')
            with open(file_path, 'r', encoding='utf-8') as file_file:
                file_text = file_file.read().strip()
            if file_text:
                print(file_text)
            print(f'</{file_path}>')

        # Directory item
        elif 'dir' in item:
            dir_path = item['dir']['path']
            dir_exts = [f'.{ext.lstrip(".")}' for ext in item['dir'].get('exts') or []]
            dir_depth = item['dir'].get('depth', 0)
            for file_path in _get_directory_files(dir_path, dir_exts, dir_depth):
                if ix_item != 0:
                    print()
                print(f'<{file_path}>')
                with open(file_path, 'r', encoding='utf-8') as file_file:
                    file_text = file_file.read().strip()
                if file_text:
                    print(file_text)
                print(f'</{file_path}>')

        # URL item
        elif 'url' in item:
            url = item['url']
            if ix_item != 0:
                print()
            print(f'<{url}>')
            with urllib.request.urlopen(item['url']) as response:
                url_text = response.read().strip().decode('utf-8')
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


class TypedItemAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # Initialize the destination list if it doesn't exist
        if not hasattr(namespace, self.dest) or getattr(namespace, self.dest) is None:
            setattr(namespace, self.dest, [])

        # Get type_id from the option string (e.g., '-p' -> 'p')
        type_id = option_string.lstrip('-')[:1]

        # Append tuple (type_id, value)
        getattr(namespace, self.dest).append((type_id, values))


FILE_PROMPT_SMD = '''\
# The file-prompt configuration file format
struct FilePromptConfig

    # The list of prompt items
    FilePromptItem[len > 0] items


# A prompt item
union FilePromptItem

    # Config file include
    string config

    # A prompt message
    string message

    # A long prompt message
    string[len > 0] long

    # File include POSIX path
    string file

    # Directory include
    FilePromptDir dir

    # URL include
    string url


# A directory include item
struct FilePromptDir

    # The directory POSIX path
    string path

    # The file extensions to include (e.g. ".py")
    string[len >= 0] exts

    # The directory traversal depth (default is 0, infinite)
    optional int(>= 0) depth
'''
FILE_PROMPT_TYPES = schema_markdown.parse_schema_markdown(FILE_PROMPT_SMD)


# Helper enumerator to recursively get a directory's files
def _get_directory_files(dir_name, file_exts, max_depth=0, current_depth=0):
    return sorted(_get_directory_files_helper(dir_name, file_exts, max_depth, current_depth))

def _get_directory_files_helper(dir_name, file_exts, max_depth, current_depth):
    # Recursion too deep?
    if max_depth > 0 and current_depth > max_depth:
        return

    # Scan the directory for files
    for entry in os.scandir(dir_name):
        if entry.is_file():
            if os.path.splitext(entry.name)[1] in file_exts:
                file_path = os.path.normpath(os.path.join(dir_name, entry.name))
                yield file_path
        elif entry.is_dir(): # pragma: no branch
            dir_path = os.path.join(dir_name, entry.name)
            yield from _get_directory_files_helper(dir_path, file_exts, max_depth, current_depth + 1)
