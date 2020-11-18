==========
Modularyze
==========


.. image:: https://img.shields.io/pypi/v/modularyze.svg
        :target: https://pypi.python.org/pypi/modularyze

.. image:: https://img.shields.io/travis/jungerm2/modularyze.svg
        :target: https://travis-ci.com/jungerm2/modularyze

.. image:: https://readthedocs.org/projects/modularyze/badge/?version=latest
        :target: https://modularyze.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Modularyze is a modular, composable and dynamic configuration engine that mixes the power of dynamic webpage rendering with that of YAML. It relies on Jinja_ and `ruamel.yaml`_ and inherits their flexibility.


Quick Start
-----------

Installation
^^^^^^^^^^^^

To install the latest version of modularyze, run this command in your terminal:

.. code-block:: console

    $ pip install modularyze


Example
^^^^^^^

The Modularize package exposes one central config-builder class called ConfBuilder_. Using this class you can register arbitrary constructors and callables, render templated multi-file and dynamic configs, instantiate them and compare configs by hash or their normalized form.

To use modularyze in a project simply import it, register any callables your config might be using and point it to your configuration file. From there you can simply call build_ to build the config.

A simple example where we instantiate a machine learning pipeline could look something like this:

.. code-block::

    # File: imagenet.yaml

    {% set use_pretrained = use_pretrained | default(True) %}
    {% set imagenet_root = imagenet_root | default('datasets/imagenet') %}

    network: &network
        !torchvision.models.resnet18
        pretrained: {{ use_pretrained }}

    val_transforms: &val_transforms
        !torchvision.transforms.Compose
        - !torchvision.transforms.Resize [256]
        - !torchvision.transforms.CenterCrop [224]
        - !torchvision.transforms.ToTensor

    dataset: &dataset
        !torchvision.transforms.datasets.ImageNet
        args:
          - {{ imagenet_root }}
        kwargs:
          split: 'val'
          transforms: *val_transforms


.. code-block:: python

    import torchvision
    from modularyze import ConfBuilder

    builder = ConfBuilder()
    builder.register_multi_constructors_from_modules(torchvision)
    conf = builder.build('imagenet.yaml')

Now the ``conf`` object is a python dictionary containing a fully initialized model, dataset and validation transforms. What about if you want to change a parameter on the fly? Say the imagenet folder changes? Easy, simply pass in a context:

.. code-block:: python

    conf = builder.build('imagenet.yaml', context={"imagenet_root": "new/path/to/dataset"})

In this way ypu can easily parameterize you configuration files. The provided context is usually a dictionary but it can even be the path to a (non-parameterized/vanilla) YAML file.

What about if we have the configuration for a model trainer in a different file? Imagine the file ``trainer.yaml`` instantiates a neural network trainer instance, we can include it by adding the following line to the above config file:

.. code-block:: jinja

    {% include 'trainer.yaml' %}

There are many more neat things you can do when you combine the powers of YAML and Jinja, please refer to the documentation_ for more.


.. _Jinja: https://jinja.palletsprojects.com/en/2.11.x/
.. _`ruamel.yaml`: https://pypi.org/project/ruamel.yaml/
.. _documentation: https://modularyze.readthedocs.io/en/latest/
.. _ConfBuilder: https://modularyze.readthedocs.io/en/latest/api.html#modularyze.modularyze.ConfBuilder/
.. _build: https://modularyze.readthedocs.io/en/latest/api.html#modularyze.modularyze.ConfBuilder.build/
