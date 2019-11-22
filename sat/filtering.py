"""
Generic output filtering utilities for SAT.

Copyright 2019 Cray Inc. All rights reserved.
"""

import fnmatch
import logging
import operator

from parsec import ParseError
import parsec

LOGGER = logging.getLogger(__name__)

# Note: this comparator matching group is order-dependent because
# Python's re module is very silly and does not use maximal munch.
COMPARATOR_RE = r'(>=|<=|<|>|!=|=)'


class FilterFunction:
    """A callable object which implements a filtering function.

    This function essentially emulates a closure which uses the
    query_key and value parsed from some query string to filter
    an input dictionary. A value can be a number (int or float)
    or a string.

    The 'query_key' argument passed to the constructor can be any
    subsequence of the desired key to filter against. The actual
    underlying dictionary key is computed the first time the function
    is called. This optimization is made since it is assumed that
    headings (i.e. keys) are identical for each dictionary in the
    iterable being filtered.
    """

    def __init__(self, query_key, comparator, cmpr_val):
        """Creates a new FilterFunction.

        Args:
            query_key: a subsequence of some key to filter against.
            comparator: a comparator string (i.e. =, !=, >, <, >=,
                or <=)
            cmpr_val: a string or number which defines the filter.
        """
        self._cmpr_fn = _get_cmpr_fn(comparator, is_number=isinstance(cmpr_val, float))
        self._cmpr_val = cmpr_val

        # The true key will be computed on the first run, so just
        # store whatever we're given here for now.
        self._raw_query_key = query_key

    def __call__(self, row):
        """Checks whether the given row matches the filter.

        Note that this function has side-effects; the query_key passed
        to the constructor can be a subsequence of the actual
        dictionary key to be filtered against, thus the underlying
        dictionary key will be computed based on the keys present in
        the first dictionary being filtered. This key will be stored
        and used in future comparisons. Care should be used if the
        same filter is applied to multiple lists with differing
        headers.

        Args:
            row: a dictionary which is to be filtered.

        Returns:
            True if row matches the filter, False otherwise.

        Raises:
            TypeError: if the value for the query key in the row can't be
                compared to the given value with the given comparison.
        """
        if not hasattr(self, '_computed_query_key'):
            self._computed_query_key = \
                _match_query_key(self._raw_query_key, row.keys())

        try:
            return self._cmpr_fn(row[self._computed_query_key],
                                 self._cmpr_val)

        except TypeError as err:
            raise TypeError("Cannot filter value of type '{}' with value "
                            "of type '{}'.".format(type(row[self._computed_query_key]).__name__,
                                                   type(self._cmpr_val).__name__)) from err


def combine_filter_fns(fns, combine_fn=all):
    """Creates a function which is the logical combination of input functions.

    Args:
        fns: iterable of functions which take a single argument
            and return a bool.
        combine_fn: a function which takes an iterable of booleans and
            returns a boolean. By default, this is `all`. (i.e., the
            logical 'and' of the input functions. For a logical 'or'
            behavior, `any` can be passed instead.

    Returns:
        a function which takes a single argument and returns
        the logical combination of all argument functions according to
        combine_fn.
    """
    def inner(x):
        return combine_fn(fn(x) for fn in list(fns))
    return inner


def _subsequence(needle, haystack):
    """Checks if needle is a subsequence of haystack.

    Informally, needle is a subsequence of haystack if needle can be
    obtained by deleting zero or more characters from haystack.

    Formally, let haystack be some sequence of characters h_1, h_2,
    ..., h_k, where k = len(haystack), and let s be some strictly
    increasing sequence of length l, where 0 <= l <= k, and for any i
    in s, 1 <= i <= k. Then needle is the sequence of characters
    h_(s_1), h_(s_2), ..., h_(s_l).

    Args:
        needle: the subsequence to look for
        haystack: the string in which to search for the subsequence

    Returns:
        True if needle is a subsequence of haystack, and False
        otherwise.
    """
    if needle and haystack:
        try:
            first, rest = needle[0], needle[1:]
            hpos = haystack.index(first)
            return _subsequence(rest, haystack[(hpos + 1):])

        except ValueError:
            # Letter from needle not found in haystack, so there's no
            # way it's a subsequence.
            return False

    else:
        return not needle


def _match_query_key(query_key, headings):
    """Computes the underlying key from some user-supplied query.

    If query_key is the subsequence of exactly one heading in
    headings, then that heading is returned. Otherwise, a KeyError is
    raised.

    Args:
        query_key: a string containing some key we want to match
        headings: an iterable containing various headings

    Returns:
        the unique key matching query_key.

    Raises:
        KeyError: if zero or multiple headings are matched
    """
    # We want to be able to match on just the subsequence of
    # query_key, since keys can be somewhat long or have extraneous
    # info (e.g. units etc.) that we don't want the user to worry
    # about.
    matching_keys = [key for key in headings
                     if _subsequence(query_key.lower(), key.lower())]
    if len(matching_keys) != 1:
        raise KeyError("Query key '{}' is invalid because it {}"
                       .format(query_key,
                               ('does not exist.' if not matching_keys
                                else 'is ambiguous. (could be one of: {})'
                                .format(', '.join(matching_keys)))))
    return matching_keys.pop()


def _str_eq_cmpr(name, pattern):
    """Compares name to pattern with wildcards.

    Comparison is case insensitive. Pattern matching is based on the
    fnmatch module.

    Args:
        name (str): some value to check.
        pattern (str): a wildcard pattern which might
            match name.

    Returns:
        bool: True if name matches the pattern after wildcard
            expansion, and False otherwise.
    """
    return fnmatch.fnmatch(str(name).lower(),
                           pattern.lower())


def _get_cmpr_fn(fn_sym, is_number=False):
    """Returns a comparator function given some symbol.

    Comparator functions are built-in operators for >, >=, <, <=, =,
    and !=. For =, if is_number is True, then the built-in equals
    operator is returned. Otherwise, a wildcard matching function is
    returned.

    If fn_sym is an unrecognized operator, ValueError is raised.

    Args:
        fn_sym: a character containing a comparison symbol.
        is_number: whether the given function should just compare
            numbers or strings.

    Returns:
        a function which implements the given comparator.

    Raises:
        ValueError: if fn_sym is not a valid operator.
    """
    fns = {
        '>':   operator.gt,
        '>=':  operator.ge,
        '<':   operator.lt,
        '<=':  operator.le,
        '!=': (operator.ne if is_number
               else lambda n, p: not _str_eq_cmpr(n, p)),
        '=':  (operator.eq if is_number
               else _str_eq_cmpr)
    }

    if fn_sym not in fns:
        raise ValueError('Invalid comparison symbol')

    return fns.get(fn_sym)


def parse_query_string(query_string):
    """Compiles a query string into a function for filtering rows.

    If query_string is invalid, ParseError is raised.

    Args:
        query_string: a string against which the rows should be
            filtered

    Returns:
        a function which returns True if a given row matches
        the query string, and False otherwise.

    Raises:
        ParseError: if query_string is not a valid query.
    """

    def lexeme(p):
        """Creates subparsers (potentially) surrounded by whitespace.

        Args:
            p: a parsec.Parser object

        Returns:
            a parser which is followed by optional whitespace.
        """
        whitespace = parsec.regex(r'\s*')
        return p << whitespace

    tok_dq = lexeme(parsec.string('"'))
    tok_sq = lexeme(parsec.string('\''))
    tok_and = lexeme(parsec.string('and'))
    tok_or = lexeme(parsec.string('or'))
    tok_cmpr = lexeme(parsec.regex(COMPARATOR_RE))
    tok_lhs = lexeme(parsec.regex(r'[a-zA-Z_]+'))

    @lexeme
    @parsec.generate
    def tok_double_quoted_str():
        """Parses a double-quoted string.

        Double-quoted strings can contain any non-double-quote
        character.

        Returns:
            a string containing the contents of the quoted string.
        """
        yield tok_dq
        content = yield parsec.regex(r'[^"]*')
        yield tok_dq

        return content

    @lexeme
    @parsec.generate
    def tok_single_quoted_str():
        """Parses a single-quoted string.

        Single-quoted strings can contain any non-single-quote
        character.

        Returns:
            a string containing the contents of the quoted string.
        """
        yield tok_sq
        content = yield parsec.regex(r'[^\']*')
        yield tok_sq

        return content

    tok_quoted_str = tok_double_quoted_str ^ tok_single_quoted_str

    @lexeme
    @parsec.generate
    def tok_rhs():
        """Parse the right hand side of an expression.

        The right hand side can be a number or some wildcard. Numbers
        are parsed into floats, and wildcards are returned as
        strings. These are handled separately from quoted strings,
        which are always interpreted as strings.

        Returns:
             a float if the value can be parsed as a number, or a
             string otherwise.
        """
        content = yield lexeme(parsec.regex(r'(\w|[*?.])+'))
        try:
            return float(content)
        except ValueError:
            return content

    @parsec.generate
    def comparison():
        r"""Parses a comparison expression (e.g. 'foo=bar')

        Comparison expressions have the following grammar, in pseudo-BNF:
            <ident> ::= tok_lhs
            <single_quoted_str> ::= ' <str> '
            <double_quoted_str> ::= " <str> "
            <wildcard> ::= tok_rhs
            <num> ::= FLOAT_RE
            <comparator> ::= '>=' | '>' | '<' | '<=' | '=' | '!='
            <cmpr_val> ::= <wildcard> | <num>
            <comparison> ::= <ident> <comparator> <cmpr_val>

        If the given value is a string, then the value in the
        row will be filtered using fnmatch.fnmatch (i.e.,
        wildcards will be expanded.) If the value is instead a
        number, a numerical comparison will be used.

        Returns:
            a function which can filter rows according to the
            comparison sub-expression which this parser parses.
        """
        # TODO: It might be a "good" idea in the future to refactor
        # the grammar a little bit to enforce types on certain
        # comparisons (e.g., only allow comparisons to numbers for
        # greater-than or less-than), but if this doesn't turn out to
        # be an issue, it probably isn't all that necessary.
        query_key = yield tok_lhs
        comparator = yield tok_cmpr
        cmpr_val = yield (tok_rhs ^ tok_quoted_str)

        return FilterFunction(query_key, comparator, cmpr_val)


    @parsec.generate
    def bool_or_expr():
        """Parses an 'or' expression. (e.g. 'foo = bar or baz > 10')

        'or' expressions have the following grammar:
            or_expr   ::= and_expr | <or_expr> "or" <and_expr>

        Returns:
            a function which can filter input rows by whether
            they match the boolean expression according to its
            constituent parts and operator.
        """
        lhs = yield or_expr
        yield tok_or
        rhs = yield and_expr
        return combine_filter_fns([comparison, and_expr],
                                   combine_fn=any)

    @parsec.generate
    def bool_and_expr():
        """Parses an 'and' expression. (e.g. 'foo = bar and baz > 10')

        'and' expressions have the following grammar:
            and_expr   ::= comparison | <and_expr> "and" <comparison>

        Returns:
            a function which can filter input rows by whether
            they match the boolean expression according to its
            constituent parts and operator.
        """
        lhs = yield and_expr
        yield tok_and
        rhs = yield comparison
        return combine_filter_fns([comparison, and_expr])

    # This should enforce operator precedence at the grammar level.
    and_expr = comparison ^ bool_and_expr
    or_expr = and_expr ^ bool_or_expr

    @parsec.generate
    def bool_expr():
        # Left hand side is always a comparison. (i.e. boolean
        # operators are always right-associative.)
        lhs = yield comparison
        oper = yield (tok_and | tok_or)

        # Right hand side can be another boolean expression; if it
        # isn't, fall back and check if it's just a single comparison
        # (i.e., the base case)
        rhs = yield (bool_expr ^ comparison)

        return combine_filter_fns([lhs, rhs],
                                  combine_fn=all if oper == 'and' else any)

    # Expressions can either be a boolean expression composing >= 2
    # comparisons, or just a single comparison.
    expr = bool_expr ^ comparison

    return expr.parse_strict(query_string)


def filter_list(dicts, query_strings):
    """Filters a list of dicts according to some query strings.

    If the filter string is invalid, then dicts will be returned as a
    list, contents unchanged. It is assumed that every dict in dicts
    will have identical keys. If not, ValueError will be raised.

    Args:
        dicts: a list or iterable of OrderedDicts which is to be
            filtered.
        query_strings: an iterable of some query strings against
            which to filter the input list.

    Returns:
        a list dicts filtered according to query_string.

    Raises:
        ValueError: if keys in dicts are inconsistent.
        ParseError: if any of query_strings is invalid.
        KeyError: if attempting to filter against an invalid key.
        TypeError: if a value for the query key can't be compared to the given
            comparison value.
    """
    if not dicts:
        return []

    if not query_strings:
        return dicts

    # Assume the first row's headings are the "right ones."
    first, rest = dicts[0], dicts[1:]
    fkeys = first.keys()
    if any(d.keys() != fkeys for d in rest):
        raise ValueError('All input dicts must have same keys.')

    all_filter_fns = [parse_query_string(query_string)
                      for query_string in query_strings]
    filter_fn = combine_filter_fns(all_filter_fns)
    return list(filter(filter_fn, dicts))
