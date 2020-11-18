.. _constructor-page:

============
Constructors
============

Modularyze allows for arbitrary objects to be instantiated and any function to be called when the config is being built. In fact, any callables will work as long as it is registered. This functionality is already partially present in YAML but is improved upon here.

Default Types
=============

You can easily check what constructors you have registered by inspecting the ``constructors`` attribute of a builder object. Note that there are some default constructors present which correspond to python native types:

.. code-block:: json
    :force:

    {
      "constructors": {
        "tag:yaml.org,2002:null": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_null(self, node)>,
        "tag:yaml.org,2002:bool": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_bool(self, node)>,
        "tag:yaml.org,2002:int": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_int(self, node)>,
        "tag:yaml.org,2002:float": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_float(self, node)>,
        "tag:yaml.org,2002:binary": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_binary(self, node)>,
        "tag:yaml.org,2002:timestamp": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_timestamp(self, node, values=None)>,
        "tag:yaml.org,2002:omap": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_omap(self, node)>,
        "tag:yaml.org,2002:pairs": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_pairs(self, node)>,
        "tag:yaml.org,2002:set": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_set(self, node)>,
        "tag:yaml.org,2002:str": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_str(self, node)>,
        "tag:yaml.org,2002:seq": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_seq(self, node)>,
        "tag:yaml.org,2002:map": <function ruamel.yaml.constructor.SafeConstructor.construct_yaml_map(self, node)>,
      },
      "multi_constructors": {}
    }

The key-value pairs here correspond to the tag/constructor (callable). Notice that these default types have long tags, yet they are common enough that these long-explicit tags are never used directly. In practice, for some of these, like the one that corresponds to lists, dictionaries or literals, YAML will call the constructor automatically (using something called implicit-resolvers). For others, such as omap (ordered-dict) and sets, you will need to use their shorthand tag which is simply the ``!!`` followed by the type (as seen in the tag's fullname). All of these are well documented on the official `YAML 1.2 Spec`_, the examples below are just intended as a quick reference.

.. code-block:: yaml
    :force:

    # Literals (implicitly resolved)
    - null
    - true
    - false
    - 12345
    - 1.234
    - 0b1010
    - my string
    - 2002-12-14

    # Datatypes (implicitly resolved)
    - [1, 2, 3]
    - {a: 1, b: 2, c: 3}

    # Datatypes (explicitly resolved)
    - !!set {1, 2, 3}
    - !!omap [a: 1, b: 2, c: 3]
    - !!pairs [a: 1, b: 2, c: 3]

.. warning::
    There are corner cases and common gotchas with these basic types. Please see :ref:`limitations <limitations-page>` for more.


Custom Types
============

Constructors vs. Multi-Constructors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

YAML defines two constructor types, single and multi. Simply put, adding a (single) constructor will allow YAML to construct a single object per tag, while a multi-constructor will specify a tag prefix.

You could register the tag ``!Module.foo`` and ``!Module.bar`` as constructors to call the two functions, foo and bar, in the Module package. You could also register the prefix-tag ``!Module`` as a multi-constructor and then use ``!Module.foo`` and ``!Module.bar`` as well.

Multi-constructors allow you to register a single (prefix) tag and then dynamically find it's members. This allows for a less cluttered tag/constructor mapping. Single constructors will pollute the tag/constructor mapping more but be more explicit.


Registering Constructors
^^^^^^^^^^^^^^^^^^^^^^^^

There's a few ways to register callables (please see the :ref:`API <api-page>` specification for more):

- :meth:`~modularyze.modularyze.ConfBuilder.register_constructors`
- :meth:`~modularyze.modularyze.ConfBuilder.register_multi_constructors`
- :meth:`~modularyze.modularyze.ConfBuilder.register_constructors_from_modules`
- :meth:`~modularyze.modularyze.ConfBuilder.register_multi_constructors_from_modules`

Each of these can register callables implicitly, when passed as arguments, or explicitly, when passed as keyword arguments.


Explicit vs Implicit Constructors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The safest and most verbose way to add constructors is to do so explicitly, however, Modularize allows for implicit tag creation. This relies on the callable's ``__name__`` attribute and as such is not guaranteed to always work as expected. Because of this, you cannot expect the following to work given a tag ``!np.<callable>``:

.. code-block:: python

    # INCORRECT!
    import numpy as np
    # ... your code here ...
    builder.register_multi_constructors_from_modules(np)

Instead, you need to explicitly define the tag or use the tag ``!numpy``.

.. code-block:: python

    # CORRECT!
    import numpy as np
    # ... your code here ...
    builder.register_multi_constructors_from_modules(**{'!np': np})

Default Constructors
^^^^^^^^^^^^^^^^^^^^

Any object that doesn't define it's own custom yaml constructor (see below) will get a default one as provided by Modularize. This constructor will parse any arguments you might have passed and then call the callable you've registered. As such, the following will work:

.. code-block:: yaml

    # No arguments
    - !myObject

    # Only positional arguments
    - !myObject [1, 2, 3]
    - !myObject
        args: [1, 2, 3]

    # Only keyword arguments
    - !myObject {a: 1, b: 2, c: 3}
    - !myObject
        kwargs: {a: 1, b: 2, c: 3}

Positional and keyword arguments can of course be mixed. Further, lists can be written with dashes one element per line and dictionaries can be written without curly braces one element per line, see the `YAML 1.2 Spec`_ for more.


Custom Constructors
^^^^^^^^^^^^^^^^^^^

If a class defines a classmethod :meth:`from_yaml` then this will be used to instantiate the object. The following class can therefore be instantiated based on it's representation, e.g: "!Dice 10d6" is valid.


.. code-block:: python

    class Dice:
        def __init__(self, a, b):
            self.a, self.b = a, b

        def __repr__(self):
            return f"Dice({self.a}, {self.b})"

        @classmethod
        def from_yaml(cls, loader, node):
            value = loader.construct_scalar(node)
            a, b = map(int, value.split('d'))
            return cls(a, b)


.. _`YAML 1.2 Spec`: https://yaml.org/spec/1.2/spec.html
