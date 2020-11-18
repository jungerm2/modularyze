.. _limitations-page:

=====================
Gotchas & Limitations
=====================

.. warning::
    More to come soon!

Gotchas
=======

Literals
^^^^^^^^

In YAML the tag that will be converted to ``None`` is ``NULL`` or ``null``. Writing ``None`` will result in a string. Similarly, a set is not just expressed as ``{1, 2, 3}``. This will yield a dictionary with values equal to None instead. To instantiate a set you should use the explicit set constructor ``!!set``.

Registering explicit constructors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Python does not allow keywords to begin with an exclamation point. Yet, YAML tags often start with a ``!``, so to explicitly register a callable you will need to unpack a dictionary like so:

.. code-block:: python
    :force:

    # Incorrect
    register_constructors(!my_func_tag=my_func)

    # Correct
    register_constructors(**{"!my_func_tag": my_func})


Jinja Directives
^^^^^^^^^^^^^^^^

We use Jinja directives quite extensively but because they are originally meant for use with HTML and not YAML there are a few things to look out for. Certain directives can create invalid YAML that won't be able to be properly parsed. A common occurrence of this is with the ``include`` directive. Consider the following two files:

.. code-block:: yaml

    # File: num_keys.yaml
    key1: value1
    key2: value2

.. code-block:: yaml

    # File: num_keys.yaml
    keyA: valueA
    keyB: valueB

If you would like to include both in another config, you could use the Jinja ``include`` directive like so:

.. code-block:: jinja

    {% include "num_keys.yaml" %}
    {% include "num_keys.yaml" %}

However, this will result in the following **incorrect** file (ignoring the comments):

.. code-block:: yaml
    :force:

    key1: value1
    key2: value2keyA: valueA
    keyB: valueB

To avoid this, you can simply add a newline between includes!

Issues like these arise because Jinja is not specific to YAML and could, in part, be alleviated with custom YAML-aware jinja directives. Currently there aren't any but this might be a future feature request.
