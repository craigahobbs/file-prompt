# Licensed under the MIT License
# https://github.com/craigahobbs/file-prompt/blob/main/LICENSE

"""
file-prompt command-line script main module
"""

import argparse
import os


def main(argv=None):
    """
    file-prompt command-line script main entry point
    """

    # Command line arguments
    parser = argparse.ArgumentParser(prog='file-prompt')
    parser.add_argument('-p', '--prompt', dest='items', action=TypedItemAction,
                        help='add the prompt message')
    parser.add_argument('-f', '--file', dest='items', action=TypedItemAction,
                        help='add the file')
    parser.add_argument('-d', '--dir', dest='items', action=TypedItemAction,
                        help='add the directory')
    parser.add_argument('-l', '--depth', metavar='N', type=int, default=3,
                        help='the maximum directory depth (default is 3)')
    parser.add_argument('-x', '--ext', metavar='EXT', action='append',
                        help='include files with the extension')
    args = parser.parse_args(args=argv)

    # Output the prompt items
    first = True
    for item_type, item_str in args.items:

        # Prompt message?
        if item_type == 'p':
            if first:
                first = False
            else:
                print()
            print(item_str)

        # File include?
        elif item_type == 'f':
            file_path = item_str
            if first:
                first = False
            else:
                print()
            print(f'<{file_path}>')
            with open(file_path, 'r', encoding='utf-8') as file_file:
                file_text = file_file.read().strip()
                if file_text:
                    print(file_text)
            print(f'</{file_path}>')

        # Directory include?
        elif item_type == 'd':
            dir_path = item_str
            for file_path in sorted(_get_directory_files(dir_path, args.depth, args.ext)):
                if first:
                    first = False
                else:
                    print()
                print(f'<{file_path}>')
                with open(file_path, 'r', encoding='utf-8') as file_file:
                    file_text = file_file.read().strip()
                    if file_text:
                        print(file_text)
                print(f'</{file_path}>')


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
def _get_directory_files(dir_name, max_depth, file_exts, current_depth=0):
    # Recursion too deep?
    if current_depth > max_depth:
        return

    # Scan the directory for files
    for entry in os.scandir(dir_name):
        if entry.is_file():
            if os.path.splitext(entry.name)[1] in file_exts:
                file_path = os.path.join(dir_name, entry.name)
                yield file_path
        elif entry.is_dir(): # pragma: no branch
            dir_path = os.path.join(dir_name, entry.name)
            yield from _get_directory_files(dir_path, max_depth, file_exts, current_depth + 1)
