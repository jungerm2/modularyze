=====
Usage
=====

Basic YAML Features
^^^^^^^^^^^^^^^^^^^

YAML is a markup specification that is a strict superset of JSON. YAML parsers can load mostly-static configuration files into python and produce an equivalent object (dict, list, etc.).

Unlike JSON, YAML allows for more complex behavior. For instance, YAML has what is known as *anchors and aliases*. These can be used to tag and reference any part of a YAML document and allows for DRY (do not repeat yourself) configs. Here's an example:

.. code-block:: yaml

    - name: John Smith
      dob: Jan 1, 1980
      parents: &smith_parents
        mother: Emily Smith
        father: Robert Smith
    - name: Alice Smith
      dob: Jan 1, 1980
      parents: *smith_parents

In the above example, we only have to specify the parents of the imaginary twins John and Alice once. Then, provided we add the anchor ``&smith_parents``, we can reference the parents with an alias ``*smith_parents``. Note that this is **not** the same thing as a variable and treating it as such can lead to unexpected errors. See [...] for more.

YAML can also instantiate (arbitrary) objects as long as we register their constructor and a tag. Modularize takes this one step further and allows any callable to be called. This allows for any object to be instantiated or any function to be called. Consider the following example:

.. code-block:: yaml

    # File: complex_nums.yaml
    - !Complex [1, 2]
    - !Complex [3, 4]
    - !Complex [5, 6]


.. code-block:: python

    # File: numbers.py
    from modularize import ConfBuilder

    class Complex:
        def __init__(self, realpart, imagpart):
            self.r = realpart
            self.i = imagpart

        def __str__(self):
            return f"{self.r}{self.i:+}i"

    builder = ConfBuilder.from_file("complex_nums.yaml")
    builder.register_constructors(Complex)

    my_numbers = builder()
    # my_numbers = [Complex(1, 2), Complex(3, 4), Complex(5, 6)]

Note that in order to instantiate any custom object we need to *register* it's constructor first. There are a number of ways to register constructors, both implicitly and explicitly, that are described :ref:`here <constructor-page>`. Here, the tag ``!Complex`` was implicitly derived from the class name but we could just as easily provide an explicit name by doing:

.. code-block:: python

    builder.register_constructors(**{"!COMPLEX-NUMBER": Complex})

However, it would be annoying to register an explicit constructor for every callable we wanted to use. To address this, Modularyze allows you to register multi-constructors from modules, you can therefore do:

.. code-block:: python

    import numpy
    # ... your code here ...
    builder.register_multi_constructors_from_modules(numpy)


.. code-block:: yaml

    N: &N 100
    identity: &I !numpy.eye [*N]
    rand_nums: !numpy.random.uniform {size: [*N, 1]}

There are a few caveats be be weary of when registering callables. Because the YAML tags ``!numpy.<something>`` are dynamically evaluated based on the module's name, we wouldn't be able to use ``import numpy as np`` and to register just ``np``. This can be done, but we would need to explicitly register the mapping ``!np -> numpy``. See :ref:`here <constructor-page>` for more.


Basic Jinja Features
^^^^^^^^^^^^^^^^^^^^

Modularize allows for configuration files to be dynamically created at runtime through Jinja's template preprocessor applied to YAML. Consider the following ``networks.yaml`` file:

.. code-block:: jinja

    # File: networks.yaml

    addresses:
      {% for i in range(256) %}
      - 127.0.0.{{ i }}
      {% endfor %}
    ports: [22, 80, 25565]


The following code will then read this file and produce the corresponding dictionary containing all addresses and ports:

.. code-block:: python

    from modularize import ConfBuilder

    builder = ConfBuilder.from_file('networks.yaml')
    conf = builder()

There's a lot more features that Jinja can provide than for-loops but one very useful jinja directive is the ``include`` tag. It can be used to compose multiple configs together:

.. code-block:: jinja

    # File: server_config.yaml

    server_name: "my super awesome server"
    connections:

      {% include "networks.yaml" %}

    protocols: [tcp, ssh, sftp]

When built like shown above this will create the full configuration which will be the following dictionary:

.. code-block:: json
    :force:

    {
      "server_name": "my super awesome server",
      "connections": {
        "addresses": ["127.0.0.0", "127.0.0.1", ..., "127.0.0.255"],
        "ports": [22, 80, 25565]
      },
      "protocols": ["tcp", "ssh", "sftp"]
    }

