#!/usr/bin/env python
"""Tests for `modularyze` package."""
# pylint: disable=redefined-outer-name

import copy
import os
import textwrap

import pytest
import ruamel.yaml
from ruamel.yaml.composer import ComposerError
from ruamel.yaml.error import YAMLError

from . import utils
from .utils import Bar, Dice, Foo

default_constructors = {
    "constructors": {
        k: v.__name__
        for k, v in ruamel.yaml.YAML(typ="safe").Constructor.yaml_constructors.items()
    },
    "multi_constructors": {
        k: v.__name__
        for k, v in ruamel.yaml.YAML(
            typ="safe"
        ).Constructor.yaml_multi_constructors.items()
    },
}

#####################################################################
#                 Basic Yaml Tests (literals, etc..)                #
#####################################################################


@pytest.mark.basic_yaml
@pytest.mark.parametrize(
    "doc, expected",
    [
        ("True", True),
        ("False", False),
        ("true", True),
        ("false", False),
        ("null", None),
        ("NULL", None),
        ("", None),
        ("''", ""),
        ("abcde", "abcde"),
        ("'12345'", "12345"),
        ("12345", 12345),
        ("3.14159", 3.14159),
    ],
)
def test_literals(builder, doc, expected):
    assert builder(doc) == expected


@pytest.mark.basic_yaml
@pytest.mark.parametrize(
    "doc, expected", [("[1, 2, 3]", [1, 2, 3]), ("- 1\n- 2\n- 3", [1, 2, 3])]
)
def test_lists(builder, doc, expected):
    assert builder(doc) == expected


@pytest.mark.basic_yaml
@pytest.mark.parametrize(
    "doc, expected",
    [
        ("{a: 1, b: 2, c: 3}", {"a": 1, "b": 2, "c": 3}),
        ("a: 1\nb: 2\nc: 3", {"a": 1, "b": 2, "c": 3}),
    ],
)
def test_dicts(builder, doc, expected):
    assert builder(doc) == expected


@pytest.mark.basic_yaml
@pytest.mark.parametrize(
    "doc, err_type, has_explainer",
    [
        ["[1, 2, 3[", YAMLError, False],
        ["- 1\n- 2\n- 3\n- *value\n- 5\n- 6", ComposerError, True],
    ],
)
def test_incorrect_yaml_gives_error(builder, doc, err_type, has_explainer):
    with pytest.raises(err_type) as excinfo:
        builder(doc)
    if has_explainer:
        assert "Error occurred around here" in str(excinfo.value)


@pytest.mark.basic_yaml
def test_vanilla_constructors(builder):
    constructors = builder._vanilla_yaml_constructors()
    constructors = {k: v.__name__ for k, v in constructors.items()}
    assert constructors == default_constructors["constructors"]


@pytest.mark.basic_yaml
def test_vanilla_multi_constructors(builder):
    constructors = builder._vanilla_yaml_multi_constructors()
    constructors = {k: v.__name__ for k, v in constructors.items()}
    assert constructors == default_constructors["multi_constructors"]


#####################################################################
#                       Simple Jinja Tests                          #
#####################################################################


@pytest.mark.basic_jinja
def test_variable(builder):
    doc = textwrap.dedent(
        """
        {% set variable = 0%}
        {{ variable }}
    """
    )
    assert builder(doc) == 0


@pytest.mark.basic_jinja
def test_include(builder):
    params = textwrap.dedent(
        """
        addr: &addr 127.0.0.1
        port: &port 8080
    """
    )

    doc = textwrap.dedent(
        """
        {% include 'params.yaml' %}

        connection:
          retries: 5
          timeout: 1
          address: *addr
          ports: [*port, ]
    """
    )

    expected = {
        "addr": "127.0.0.1",
        "port": 8080,
        "connection": {
            "retries": 5,
            "timeout": 1,
            "address": "127.0.0.1",
            "ports": [8080],
        },
    }

    dir_setup = dict(file_paths=["params.yaml"], file_contents=[params])
    print(builder(doc, **dir_setup), type(builder(doc, **dir_setup)))
    assert builder(doc, **dir_setup) == expected


@pytest.mark.basic_jinja
def test_conditional(builder):
    doc = textwrap.dedent(
        """
        {% if True %}
        a: 1
        {% else %}
        b: 2
        {% endif %}
    """
    )

    expected = {"a": 1}
    assert builder(doc) == expected


@pytest.mark.basic_jinja
def test_loop(builder):
    doc = textwrap.dedent(
        """
        {% for i in range(100) %}
        - {{ i }}
        {% endfor %}
    """
    )

    expected = list(range(100))
    assert builder(doc) == expected


@pytest.mark.basic_jinja
def test_context_from_string(builder):
    doc = textwrap.dedent(
        """
        {% for i in range(N) %}
        - {{ N }}
        {% endfor %}
    """
    )
    N = 100
    expected = [N] * N
    assert builder(doc, context={"N": N}) == expected


@pytest.mark.basic_jinja
def test_context_from_file(tmp_dir, builder):
    doc = textwrap.dedent(
        """
        {% for i in range(N) %}
        - {{ N }}
        {% endfor %}
    """
    )
    N, fname = 100, "params.yaml"
    expected = [N] * N
    tmp_dir.write(fname, f"N: {N}".encode())
    full_path = os.path.join(tmp_dir.path, fname)
    assert builder(doc, context=full_path) == expected
    assert builder(doc, context=f"N: {N}") == expected


#####################################################################
#                          Constructor Tests                        #
#####################################################################


@pytest.mark.constructors
@pytest.mark.parametrize("doc", ["!Foo", "!Foo []"])
def test_constructor_simple(builder, doc):
    builder.register_constructors(Foo)
    assert isinstance(builder(doc), Foo)


@pytest.mark.constructors
@pytest.mark.parametrize("tag", ["!Foo", "!Bar"])
def test_named_constructor_simple(builder, tag):
    builder.register_constructors(**{tag: Foo})
    assert isinstance(builder(tag), Foo)


@pytest.mark.constructors
def test_explicit_constructor_simple(builder):
    builder.register_constructors(Dice)
    d = builder("!Dice 10d6")
    assert isinstance(d, Dice)
    assert (d.a, d.b) == (10, 6)


@pytest.mark.constructors
def test_constructor_duplicate_give_no_warning(builder):
    with pytest.warns(None) as record:
        builder.register_constructors(Foo, **{"!Foo": Foo})
    assert not record


@pytest.mark.constructors
def test_constructor_override_gives_warning(builder):
    with pytest.warns(RuntimeWarning):
        builder.register_constructors(Foo, **{"!Foo": Bar})

    with pytest.warns(RuntimeWarning):
        builder.register_constructors(Foo)
        builder.register_constructors(**{"!Foo": Bar})


@pytest.mark.constructors
@pytest.mark.parametrize(
    "doc, expected",
    [
        # Single arg
        ["!Foo [[1, 2, 3]]", ([1, 2, 3],)],
        ["!Foo\nargs: [[1, 2, 3]]", ([1, 2, 3],)],
        ["!Foo\n- - 1\n  - 2\n  - 3", ([1, 2, 3],)],
        ["!Foo\nargs:\n  - - 1\n    - 2\n    - 3", ([1, 2, 3],)],
        ["!Foo [{a: 1, b: 2, c: 3}]", ({"a": 1, "b": 2, "c": 3},)],
        ["!Foo\nargs:\n  - {a: 1, b: 2, c: 3}", ({"a": 1, "b": 2, "c": 3},)],
        ["!Foo\nargs:\n  - a: 1\n    b: 2\n    c: 3", ({"a": 1, "b": 2, "c": 3},)],
        # Multi arg
        ["!Foo [a, b, c, NULL, True, False]", ("a", "b", "c", None, True, False)],
        ["!Foo\nargs:\n  - a\n  - b\n  - c", ("a", "b", "c")],
    ],
)
def test_constructor_with_only_args(builder, doc, expected):
    builder.register_constructors(Foo)
    conf = builder(doc)
    assert isinstance(conf, Foo)
    assert conf.args == expected


@pytest.mark.constructors
@pytest.mark.parametrize(
    "doc, expected",
    [
        ["!Foo {a: 1, b: 2, c: 3}", {"a": 1, "b": 2, "c": 3}],
        ["!Foo\nkwargs: {a: 1, b: 2, c: 3}", {"a": 1, "b": 2, "c": 3}],
        ["!Foo\na: 1\nb: 2\nc: 3", {"a": 1, "b": 2, "c": 3}],
        ["!Foo\nkwargs:\n  a: 1\n  b: 2\n  c: 3", {"a": 1, "b": 2, "c": 3}],
    ],
)
def test_constructor_with_only_kwargs(builder, doc, expected):
    builder.register_constructors(Foo)
    conf = builder(doc)
    assert isinstance(conf, Foo)
    assert conf.kwargs == expected


@pytest.mark.constructors
@pytest.mark.parametrize(
    "doc, expected_args, expected_kwargs",
    [
        [
            "!Foo\nargs: [1, 2, 3]\nkwargs: {a: 1, b: 2, c: 3}",
            (1, 2, 3),
            {"a": 1, "b": 2, "c": 3},
        ]
    ],
)
def test_constructor_with_args_kwargs(builder, doc, expected_args, expected_kwargs):
    builder.register_constructors(Foo)
    conf = builder(doc)
    assert isinstance(conf, Foo)
    assert conf.args == expected_args
    assert conf.kwargs == expected_kwargs


@pytest.mark.constructors
def test_nested_constructor(builder):
    builder.register_constructors(Foo)
    conf = builder("!Foo\n- !Foo")
    assert isinstance(conf, Foo)
    assert len(conf.args) == 1
    assert isinstance(conf.args[0], Foo)


@pytest.mark.constructors
def test_constructor_from_modules(builder):
    builder.register_constructors_from_modules(**{"!utils": utils})
    conf = builder("- !utils.Foo\n- !utils.Bar")
    assert isinstance(conf[0], Foo)
    assert isinstance(conf[1], Bar)


#####################################################################
#                       Multi-Constructor Tests                     #
#####################################################################


@pytest.mark.multi_constructors
def test_multi_constructor_simple(builder):
    builder.register_multi_constructors(utils)
    assert isinstance(builder(f"!{utils.__name__}.Bar"), Bar)


@pytest.mark.multi_constructors
def test_named_multi_constructor_simple(builder):
    builder.register_multi_constructors(**{"!utils": utils})
    assert isinstance(builder("!utils.Bar"), Bar)


@pytest.mark.multi_constructors
def test_explicit_multi_constructor_simple(builder):
    builder.register_multi_constructors(**{"!utils": utils})
    d = builder("!utils.Dice 10d6")
    assert isinstance(d, Dice)
    assert (d.a, d.b) == (10, 6)


@pytest.mark.multi_constructors
def test_multi_constructors_from_modules(builder):
    builder.register_multi_constructors_from_modules(**{"!utils": utils})
    assert isinstance(builder("!utils.Bar"), Bar)


@pytest.mark.multi_constructors
def test_constructors_register_correctly(builder):
    builder._reset_yaml_constructors()
    builder.register_constructors(**{"!a": Foo, "!b": Bar})
    builder.register_multi_constructors(**{"!utils": utils})

    expected_constructors = copy.deepcopy(default_constructors["constructors"])
    expected_constructors.update({"!a": "from_yaml", "!b": "from_yaml"})
    constructors = {
        k: v.__name__ for k, v in builder.constructors["constructors"].items()
    }
    assert constructors == expected_constructors

    expected_multi_constructors = copy.deepcopy(
        default_constructors["multi_constructors"]
    )
    expected_multi_constructors.update({"!utils": "from_yaml"})
    constructors = {
        k: v.__name__ for k, v in builder.constructors["multi_constructors"].items()
    }
    assert constructors == expected_multi_constructors


#####################################################################
#                         Normalization Tests                       #
#####################################################################


@pytest.mark.normalization
@pytest.mark.parametrize(
    "doc, expected",
    [
        [
            "!Foo {a: 1, b: 2, c: 3}",
            '{\n  "!Foo": {\n    "a": 1,\n    "b": 2,\n    "c": 3\n  }\n}',
        ],
        [
            "!Foo\nkwargs: {a: 1, b: 2, c: 3}",
            '{\n  "!Foo": {\n    "kwargs": {\n      "a": 1,\n      "b": 2,\n      "c": 3\n    }\n  }\n}',
        ],
        [
            "!Foo\na: 1\nb: 2\nc: 3",
            '{\n  "!Foo": {\n    "a": 1,\n    "b": 2,\n    "c": 3\n  }\n}',
        ],
        [
            "!Foo\nkwargs:\n  a: 1\n  b: 2\n  c: 3",
            '{\n  "!Foo": {\n    "kwargs": {\n      "a": 1,\n      "b": 2,\n      "c": 3\n    }\n  }\n}',
        ],
    ],
)
def test_normalize(builder, doc, expected):
    builder.register_constructors(Foo)
    conf = builder.normalize(doc)
    assert conf == expected


@pytest.mark.normalization
@pytest.mark.parametrize(
    "doc, expected",
    [
        ["!Foo {a: 1, b: 2, c: 3}", {"!Foo": {"a": 1, "b": 2, "c": 3}}],
        [
            "!Foo\nkwargs: {a: 1, b: 2, c: 3}",
            {"!Foo": {"kwargs": {"a": 1, "b": 2, "c": 3}}},
        ],
        ["!Foo\na: 1\nb: 2\nc: 3", {"!Foo": {"a": 1, "b": 2, "c": 3}}],
        [
            "!Foo\nkwargs:\n  a: 1\n  b: 2\n  c: 3",
            {"!Foo": {"kwargs": {"a": 1, "b": 2, "c": 3}}},
        ],
    ],
)
def test_normalize_raw(builder, doc, expected):
    builder.register_constructors(Foo)
    conf = builder.normalize(doc, raw=True)
    assert conf == expected


@pytest.mark.normalization
@pytest.mark.parametrize(
    "doc, expected",
    [
        # ["!Foo {a: 1, b: 2, c: 3}", 786692855875585880],
        # ["!Foo\nkwargs: {a: 1, b: 2, c: 3}", 2279317426085501800],
        # ["!Foo\na: 1\nb: 2\nc: 3", 786692855875585880],
        # ["!Foo\nkwargs:\n  a: 1\n  b: 2\n  c: 3", 2279317426085501800],
        ["!Foo {a: 1, b: 2, c: 3}", 3002588688],
        ["!Foo\nkwargs: {a: 1, b: 2, c: 3}", 2624007293],
        ["!Foo\na: 1\nb: 2\nc: 3", 3002588688],
        ["!Foo\nkwargs:\n  a: 1\n  b: 2\n  c: 3", 2624007293],
    ],
)
def test_hash(builder, doc, expected):
    builder.register_constructors(Foo)
    conf = builder.hash(doc) & 0xFFFFFFFF
    assert conf == expected
