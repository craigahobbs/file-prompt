# ctxkit

[![PyPI - Status](https://img.shields.io/pypi/status/ctxkit)](https://pypi.org/project/ctxkit/)
[![PyPI](https://img.shields.io/pypi/v/ctxkit)](https://pypi.org/project/ctxkit/)
[![GitHub](https://img.shields.io/github/license/craigahobbs/ctxkit)](https://github.com/craigahobbs/ctxkit/blob/main/LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ctxkit)](https://pypi.org/project/ctxkit/)

ctxkit is a command line tool for constructing AI prompts containing files, directories, and URLs. For example:

```
ctxkit -m "Please review the following source code file." -f main.py
```

The `-m` argument includes the message text with the generated prompt. The `-f` argument includes
the text of the given file, in this case `main.py`.


## Usage

Using the `ctxkit` command line application, you add any number or ordered *context items* of the
following types: configuration files (`-c`), messages (`-m`), URLs (`-u`), files (`-f`), and
directories (`-d`).

```
usage: ctxkit [-h] [-g] [-c PATH] [-m TEXT] [-u URL] [-f PATH] [-d PATH]
              [-x EXT] [-l N] [-v VAR EXPR]

options:
  -h, --help          show this help message and exit
  -g, --config-help   display the ctxkit config file format
  -c, --config PATH   include the ctxkit config
  -m, --message TEXT  include the prompt message
  -u, --url URL       include the URL
  -f, --file PATH     include the file
  -d, --dir PATH      include a directory's files
  -x, --ext EXT       include files with the extension
  -l, --depth N       the maximum directory depth, default is 0 (infinite)
  -v, --var VAR EXPR  define a message variable (reference with "{{var}}")
```


### Message Variables

You can specify one or more variable in a message's text using the syntax, `{{var}}`. A variable's
value is specified using the `-v` argument. For example:

```
ctxkit -v package ctxkit -m 'Write a 100 word or less description of the Python "{{package}}"'
```


## Configuration Files

The ctxkit JSON configuration file allows you to contruct complex prompts in a file, potentially
using message variables for adding specialization.

The ctxkit `-g` argument outputs the JSON configuration file format defined using the
[Schema Markdown Language](https://craigahobbs.github.io/schema-markdown-js/language/).

```
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

    # Set a message variable (reference with "{{var}}")
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
```


## Development

This package is developed using [python-build](https://github.com/craigahobbs/python-build#readme).
It was started using [python-template](https://github.com/craigahobbs/python-template#readme) as follows:

~~~
template-specialize python-template/template/ ctxkit/ -k package ctxkit -k name 'Craig A. Hobbs' -k email 'craigahobbs@gmail.com' -k github 'craigahobbs' -k noapi 1
~~~
