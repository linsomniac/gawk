# TextChomp Text Processing Library

## Overview

This is a text processing library inspired by the AWK tool, in a Python
style.  It is currently a work in progress, exploring different ways of
achieving this.  The library may change significantly as it matures.

## Abilities

- Read lines from an input.

- Call a function if a regex is matched.

- Call a function on every line between a start and end regex.

- Enrich lines from the input such as what line number in the input it came
  from.  Pipeline elements can enrich it as well, such as "split()" to set
  a "fields" attribute on the line containing the split-out fields.

## Snippets

Print out lines that start with "a":

```python
t = textchomp.TextChomp(sys.stdin)
#  This is how you call decorators without the next line being a function
t.pattern(r'^a')()
t.run()
```

OR:

```python
t = textchomp.TextChomp(sys.stdin)
t.grep(r'^a')
```

Select lines that start with "a" and save off lines within it that contain a
"q" to "t.context.data":

```python
t = textchomp.TextChomp(sys.stdin)
t.grep(r'^a')

t.context.data = ''
@t.pattern(r'q')
def line(context, line):
    context.data += line
t.run()
```

The context includes the regex match.  The line data is a string subclass with
some extra attributes for line numbers and extracting fields:

```python
t = textchomp.TextChomp(sys.stdin).split()
@t.pattern(r'hello (\S+)')
def line(context, line):
    print(
        'Line {} says hello to {}.  Field 3 is: {}'.format(
        line.line_number, context.regex.group(1), line.fields[2]))
t.run()
```

Display username and password for "/etc/passwd" lines that
start with "s":

```python
t = textchomp.TextChomp(sys.stdin).split(':')
@t.pattern(r'^s')
def show(ctx, line):
    print('{0} uid={2}'.format(*line.fields))
t.run()
```

When a line contains "CREATE TABLE", save it and the remaining lines up until
a closing paren and semi-colon into "t.context.data".  This parses out the
table creation from a SQL schema.

Within a range there is an addition context that includes the line number
within the range, and if it is the last line.  So we can add line numbers and
print the create statement at the end:

```python
t = textchomp.TextChomp(sys.stdin)
t.context.data = ''

@t.range(r'CREATE TABLE', r'\);')
def line(context, line):
    context.data += (('line %d:' % context.range.line_number) + line)
    if context.range.is_last_line:
        print(context.data)
        context.data = ''
t.run()
```

There is also a FileFollower which implements "tail -F" functionality.
It will look for new data to be appended to the file, and will re-open
the file if it shrinks, or a new file is created in place of the old.
Simple "tail +0 -F" implementation:

```python
for line in textchomp.FileFollower('/var/log/syslog'):
    print(line.rstrip())
```

Emulate the Unix "uniq" command, read stdin and drop duplicated lines:

```python
t = textchomp.TextChomp(sys.stdin)
t.context.lastline = ''

@t.eval('lastline != line')
def unique(ctx, line):
    sys.stdout.write(line)
    ctx.lastline = line
t.run()
```

## Examples

There are some example programs in the "Examples" directory:

- "css_colors_to_rgba" - Read lines with CSS colors in the in the form
  "#000000" or "#000" and convert them to "rgba(0, 0, 0, 0.3)".

- "extract_db_tables" - Read a database dump and extract out the "CREATE TABLE"
  commands to reproduce the schema.  This is an example of the "range()"
  decorator.

- "uniq" - Read stdin and output unique lines, lines the same as the previous are
  dropped.

## Future Projects

Here are some areas I'm trying to figure out whether they make sense
and if so, how to best implement them:

- More examples.
- @always() instead of "@pattern()"?
- Some way to have the matching decorators match on fields rather than the
  whole line.  "$2 ~= /^foo/ { code; }".  Maybe "@pattern(textchomp.Field(2),
  r'^foo')" or "@pattern(r'^foo', '$2')" or "field(2, r'foo')"?
  Is this done by eval(), or should this be a special case because it is
  used so often.  Might be especially useful with JSON or CSV filter.
- FS (Field Separator) and RS (Record Seperator)?  Currently the fields are
  implemented by str.split(), which can take things other than whitespace.
  RS may mean that multiple lines are handed to the processing rules, which
  I don't know exactly how that makes sense in the current setup.  For
  example, FS="\n" and RS="", for processing addresses separated by blank
  lines.
- Negate patterns.  Or just "not()" or "notpattern()"?  Or a "not()" wrapper
  around regexes?
- OFS/ORS?  These are output versions of the above, which means that there
  needs to be some way to do the equivalent of "print" or "print $1 $3, $5".
- Plugable field/record modules could allow much richer options, like a CSV
  input source, JSON, htpasswd/passwd, or even dbapi input or output.  But
  does that make sense?  CSV and JSON do.
- Can the line be changed in the processing functions like it can in AWK?
  Make it so that the fields can be updated too.
- "always" decorator (like "{code}") rather than "pattern()"?  Might be clearer.
- Else decorator for if no pattern matched?
- How to implement default print like "awk 'length > 80'" to print lines
  longer than 80, or "awk 'NF > 7'".  Maybe decorators vs like the grep()
  mix-in.
  Maybe: pattern() and the like could take as the argument:
    - String: Interpreted as a regex.
    - Otherwise, call it with the line?  But how do we get the context in there?
      Kind of want the context on the line so it can call re.match() or the like.
    - If return from above is truthy, call the decorated function.
    - BUT, if return was a SRE match, set that in the context.
