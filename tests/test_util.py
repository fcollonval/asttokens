# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import ast
import io
import token
import unittest

import astroid
import pytest
import six

from .context import asttokens
from .tools import get_node_name


class TestUtil(unittest.TestCase):

  def print_timing(self):
    # pylint: disable=no-self-use
    # Test the implementation of asttokens.util.walk, which uses the same approach as
    # visit_tree(). This doesn't run as a normal unittest, but if you'd like to see timings, e.g.
    # after experimenting with the implementation, run this to see them:
    #
    #     nosetests -i print_timing -s tests.test_util
    #
    import timeit
    import textwrap
    setup = textwrap.dedent(
      '''
      import ast, asttokens
      source = "foo(bar(1 + 2), 'hello' + ', ' + 'world')"
      atok = asttokens.ASTTokens(source, parse=True)
      ''')
    print("ast", sorted(timeit.repeat(
      setup=setup, number=10000,
      stmt='len(list(ast.walk(atok.tree)))')))
    print("util", sorted(timeit.repeat(
      setup=setup, number=10000,
      stmt='len(list(asttokens.util.walk(atok.tree)))')))


  source = "foo(bar(1 + 2), 'hello' + ', ' + 'world')"

  def test_walk_ast(self):
    atok = asttokens.ASTTokens(self.source, parse=True)

    def view(node):
      return "%s:%s" % (get_node_name(node), atok.get_text(node))

    scan = [view(n) for n in asttokens.util.walk(atok.tree)]
    self.assertEqual(scan, [
      "Module:foo(bar(1 + 2), 'hello' + ', ' + 'world')",
      "Expr:foo(bar(1 + 2), 'hello' + ', ' + 'world')",
      "Call:foo(bar(1 + 2), 'hello' + ', ' + 'world')",
      'Name:foo',
      'Call:bar(1 + 2)',
      'Name:bar',
      'BinOp:1 + 2',
      'Constant:1',
      'Constant:2',
      "BinOp:'hello' + ', ' + 'world'",
      "BinOp:'hello' + ', '",
      "Constant:'hello'",
      "Constant:', '",
      "Constant:'world'"
    ])

  def test_walk_astroid(self):
    atok = asttokens.ASTTokens(self.source, tree=astroid.builder.parse(self.source))

    def view(node):
      return "%s:%s" % (get_node_name(node), atok.get_text(node))

    scan = [view(n) for n in asttokens.util.walk(atok.tree)]
    self.assertEqual(scan, [
      "Module:foo(bar(1 + 2), 'hello' + ', ' + 'world')",
      "Expr:foo(bar(1 + 2), 'hello' + ', ' + 'world')",
      "Call:foo(bar(1 + 2), 'hello' + ', ' + 'world')",
      'Name:foo',
      'Call:bar(1 + 2)',
      'Name:bar',
      'BinOp:1 + 2',
      'Const:1',
      'Const:2',
      "BinOp:'hello' + ', ' + 'world'",
      "BinOp:'hello' + ', '",
      "Const:'hello'",
      "Const:', '",
      "Const:'world'"
    ])


  def test_replace(self):
    self.assertEqual(asttokens.util.replace("this is a test", [(0, 4, "X"), (8, 9, "THE")]),
                     "X is THE test")
    self.assertEqual(asttokens.util.replace("this is a test", []), "this is a test")
    self.assertEqual(asttokens.util.replace("this is a test", [(7,7," NOT")]), "this is NOT a test")

    source = "foo(bar(1 + 2), 'hello' + ', ' + 'world')"
    atok = asttokens.ASTTokens(source, parse=True)
    names = [n for n in asttokens.util.walk(atok.tree) if isinstance(n, ast.Name)]
    strings = [n for n in asttokens.util.walk(atok.tree) if isinstance(n, ast.Str)]
    repl1 = [atok.get_text_range(n) + ('TEST',) for n in names]
    repl2 = [atok.get_text_range(n) + ('val',) for n in strings]
    self.assertEqual(asttokens.util.replace(source, repl1 + repl2),
                     "TEST(TEST(1 + 2), val + val + val)")
    self.assertEqual(asttokens.util.replace(source, repl2 + repl1),
                     "TEST(TEST(1 + 2), val + val + val)")


def test_expect_token():
  atok = asttokens.ASTTokens("a", parse=True)
  tok = atok.tokens[0]
  with pytest.raises(ValueError):
    asttokens.util.expect_token(tok, token.OP)


if six.PY3:
  def test_combine_tokens():
    from tokenize import TokenInfo, generate_tokens, ERRORTOKEN, OP, NUMBER, NAME
    from asttokens.util import combine_tokens, patched_generate_tokens

    text = "℘·2=1"
    original_tokens = list(generate_tokens(io.StringIO(text).readline))[:4]
    assert original_tokens == [
      TokenInfo(ERRORTOKEN, string='℘', start=(1, 0), end=(1, 1), line='℘·2=1'),
      TokenInfo(ERRORTOKEN, string='·', start=(1, 1), end=(1, 2), line='℘·2=1'),
      TokenInfo(NUMBER, string='2', start=(1, 2), end=(1, 3), line='℘·2=1'),
      TokenInfo(OP, string='=', start=(1, 3), end=(1, 4), line='℘·2=1'),
    ]
    assert combine_tokens(original_tokens[:1]) == [
      TokenInfo(NAME, string='℘', start=(1, 0), end=(1, 1), line='℘·2=1'),
    ]
    assert combine_tokens(original_tokens[:2]) == [
      TokenInfo(NAME, string='℘·', start=(1, 0), end=(1, 2), line='℘·2=1'),
    ]
    assert combine_tokens(original_tokens[:3]) == [
      TokenInfo(NAME, string='℘·2', start=(1, 0), end=(1, 3), line='℘·2=1'),
    ]

    assert list(patched_generate_tokens(iter(original_tokens))) == [
      TokenInfo(NAME, string='℘·2', start=(1, 0), end=(1, 3), line='℘·2=1'),
      TokenInfo(OP, string='=', start=(1, 3), end=(1, 4), line='℘·2=1'),
    ]
    assert list(patched_generate_tokens(iter(original_tokens[:-1]))) == [
      TokenInfo(NAME, string='℘·2', start=(1, 0), end=(1, 3), line='℘·2=1'),
    ]


if __name__ == "__main__":
  unittest.main()
