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
    parser.add_argument('file', metavar='FILE', nargs='*',
                        help='the files to include in the prompt')
    parser.add_argument('-p', '--prompt', metavar='MSG',
                        help='the prompt message text')
    parser.add_argument('-s', '--suffix', metavar='MSG',
                        help='the prompt suffix message text')
    parser.add_argument('-d', '--dir', metavar='DIR', action='append',
                        help='the directories to include in the prompt')
    parser.add_argument('-l', '--depth', metavar='N', type=int, default=2,
                        help='the maximum directory depth (default is 2)')
    parser.add_argument('-x', '--ext', metavar='EXT', action='append',
                        help='include files with the extension')
    args = parser.parse_args(args=argv)

    # The prompt prefix
    if args.prompt:
        print(args.prompt)

    # Include the files
    if args.file:
        for file_path in args.file:
            print()
            print(f'<{file_path}>')
            with open(file_path, 'r', encoding='utf-8') as file_file:
                print(file_file.read())
            print(f'</{file_path}>')

    # Include the directories
    if args.dir:
        for dir_path in args.dir:
            for file_path in sorted(_get_directory_files(dir_path, args.depth, args.ext)):
                print()
                print(f'<{file_path}>')
                with open(file_path, 'r', encoding='utf-8') as file_file:
                    print(file_file.read())
                print(f'</{file_path}>')

    # The prompt suffix
    if args.suffix:
        print()
        print(args.suffix)


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
