# BareScript Tips

Here are a few tips for generating BareScript code:

1. Multi-line BareScript statements require the use of the line-continuation character, `\\`.
   Function definitions, for loops, while loops, and if-else conditionals are not considered
   multi-line statements and so do not require the line-continuation character. For example:

   ```barescript
   function myAppFunction():
       items = objectNew( \\
           'A', 1, \\
           'B', 2 \\
       )
       for item in objectKeys(items):
           markdownPrint('', '- ' + item)
       endfor
   endfunction
   ```

2. The `windowClipboardWrite` function is `async` and any function that calls it must be `async` as
   well. For example:

   ```barescript
   function myAppCopyText(text):
       windowClipboardWrite(text)
   endfunction
   ```

3. There are no inline function definitions in BareScript. All functions must be defined in the
   global scope. For example:

   ```barescript
   function myAppMessage(name):
       return 'Hello, ' + name + '!'
   endfunction
   ```

4. There is no `await` keyword in BareScript - it is implicit when calling `async` functions.

5. Generate application code as Markdown content containing only a single `markdown-script`
   code-block. For example:

   ```markdown-script
   function myAppMain():
       # ...
   endfunction

   myAppMain()
   ```

6. Please use common BareScript best practices:

   - Use lower-case, camel-case for variables and function names
   - Prefix your globals with your application prefix (e.g. `myAppCategories`)
   - Define your main entry point in a "main" function (e.g. `myAppMain`)

   For example:

   ```barescript
   function myAppMain():
       # Render the title
       title = 'Hello, World!'
       documentSetTitle(title)
       markdownPrint('# ' + markdownEscape(title))

       # Render the names
       for name in myAppNames:
           markdownPrint('', 'Hello, ' + name + '!')
       endfor
   endfunction

   # The names to say "hello" to
   myAppNames = arrayNew( \\
       'World', \\
       'Pussy Cat' \\
   )

   myAppMain()
   ```
