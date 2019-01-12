#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from .objects import (Context, String,)

import sys


class StringIterator:
    '''INTERNAL: Wrapper that converts str()s to String()s.
    This is used on the inner-most layer of the TextChomp pipeline to
    convert the input lines into rich TextChomp.String() objects containing
    the line number.

    :param data: Iterator that this class wraps.
    '''
    def __init__(self, data):
        self.data = data
        self.lineno = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.lineno += 1
        return String(self.data.__next__(), self.lineno)


class PatternIterator:
    '''INTERNAL: Pipeline Iterator wrapper implementing @pattern()
    Pipeline component that checks lines coming from the remainder
    of the pipeline and, if the pattern matches, calls a function for
    processing.

    :param program: The pipeline to consume lines from.
    :param context: Context() for passing to the function.  A "regex"
            attribute is set for the function call which has the regex
            match() object.
    :param body: The function to be run on pattern matches.
    :param pattern: A regular expression to match.
    '''
    def __init__(self, program, context, body, pattern):
        self.program = program
        self.context = context
        self.body = body
        self.pattern = pattern

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self.program)
        m = self.pattern(line)
        if m:
            self.context.regex = m
            self.body(self.context, line)
            del(self.context.regex)
        return line


class EveryIterator:
    '''INTERNAL: Pipeline Iterator wrapper implementing @every()
    This pipeline component calls the wrapped function for every
    incoming record.

    :param program: The pipeline to consume lines from.
    :param context: Context() for passing to the function.  A "regex"
            attribute is set for the function call which has the regex
            match() object.
    :param body: The function to be run on pattern matches.
    '''
    def __init__(self, program, context, body):
        self.program = program
        self.context = context
        self.body = body

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self.program)
        self.body(self.context, line)
        return line


class CodeIterator:
    '''INTERNAL: Pipeline Iterator wrapper implementing @eval()
    Pipeline component that checks lines coming from the remainder
    of the pipeline and, if the code evaluates true, calls a function
    for processing.

    :param program: The pipeline to consume lines from.
    :param context: Context() for passing to the function.  A "regex"
            attribute is set for the function call which has the regex
            match() object.
    :param body: The function to be run on pattern matches.
    :param code: (str) Code to run that determines if function is run.
    '''
    def __init__(self, program, context, body, code):
        self.program = program
        self.context = context
        self.body = body
        self.code = code

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self.program)
        self.context.line = line
        ret = eval(self.code, None, vars(self.context))
        del(self.context.line)
        if ret:
            self.context.eval = ret
            self.body(self.context, line)
            del(self.context.eval)
        return line


class RangeIterator:
    '''INTERNAL: Pipeline Iterator wrapper implementing @range()
    Pipeline component that checks lines coming from the remainder
    of the pipeline and, if the pattern matches, calls a function for
    processing.

    :param program: The pipeline to consume lines from.
    :param context: Context() for passing to the function.  For the
            life of the range, a "range" sub-context is set with
            "line_number" and "is_last_line" attributes.  The "regex"
            attribute has the start match object for every line except
            the one matching the end regex, where it is that match.
    :param body: The function to be run on all lines within the range.
    :param start: A regular expression matching the start of the range.
    :param end: A regular expression matching the end of the range.
    '''
    def __init__(self, program, context, body, start, end):
        self.program = program
        self.context = context
        self.body = body
        self.start = start
        self.end = end
        self.in_range = False

    def __iter__(self):
        return self

    def _engine(self, line):
        '''INTERNAL: Code implementing the range state machine.
        This detects the start of the range, calls the function until the
        end matches.
        '''
        if not self.in_range:
            m = self.start(line)
            if not m:
                return
            self.in_range = True
            self.context.range = Context()
            self.context.range.regex = m
            self.context.range.line_number = 0
            self.context.range.is_last_line = False

        self.context.range.line_number += 1
        m = self.end(line)
        if m:
            self.context.range.regex = m
            self.context.range.is_last_line = True
        self.body(self.context, line)
        if not m:
            return
        self.in_range = False
        del(self.context.range)

    def __next__(self):
        line = next(self.program)
        self._engine(line)
        return line


def _print(context, line):
    '''INTERNAL: Default action which is used internally to print matches.
    This is the default if a decorator is called as a function rather than
    with "@pattern('match')", you use:

    t.pattern('match')()

    This is how Python accesses decorators with no associated function.
    '''
    sys.stdout.write(line)