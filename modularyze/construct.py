import operator

from ruamel.yaml.nodes import MappingNode, ScalarNode, SequenceNode

# TODO:
#   - function references
#   - Implicit resolvers?


def from_yaml_constructor(cls):
    """YAML Constructor factory: create default `from_yaml`
    constructor for a callable and interpret the arguments
    as follows:

    if the node is a scalar:
        - no args if the node value evaluates to False
        - single argument otherwise
    if the node is a sequence:
        - multiple args
    if the node is a mapping:
        - only kwargs
        - both args/kwargs, in which case the mapping should
            be {'args': [....], 'kwargs': {...}}

    TODO: What about keyword only arguments?
    """

    def from_yaml(loader, node):
        if isinstance(node, ScalarNode):
            # The callable only has one argument
            value = loader.construct_scalar(node)
            return cls(value) if value else cls()
        if isinstance(node, SequenceNode):
            # The callable only has positional arguments
            args = loader.construct_sequence(node, deep=True)
            return cls(*args)
        if isinstance(node, MappingNode):
            # The callable has both or only keyword arguments
            params = loader.construct_mapping(node, deep=True)
            args = params.get("args", [])
            kwargs = params.get("kwargs", {})
            if not args:
                # received only kwargs, if `kwargs` is empty then
                # use all `params` as kwargs, if not we are in a scenario
                # where there's something like:
                # !Foo
                # kwargs: {a: 1, b: 2, c: 3}
                # In which case we need to use `kwargs`.
                if kwargs:
                    return cls(**kwargs)
                return cls(**params)
            return cls(*args, **kwargs)

    return from_yaml


def from_yaml_multi_constructor(module, attr_sep="."):
    """Similar to `from_yaml_constructor` except it works with
    multi-constructors, that is, the dispatch to the correct
    constructor is done through the tag-suffix.

    Example: if you have a module named `Foo` with callables
        `A` and `B` in it, you can you only need to add the
        multi-constructor with prefix `!Foo.` and constructor
        `from_yaml_multi_constructor(Foo)` for the following
        tags to work as expected: `!Foo.A`, `!Foo.B`

        This is more efficient than registering a constructor
        for `A` and `B` individually as you don't need to import
        these for this to work, they are loaded automatically.
    """

    def from_yaml(loader, tag_suffix, node):
        # Get attribute even if it's nested
        tag_suffix = tag_suffix.lstrip(attr_sep)
        if not tag_suffix:
            cls = module
        else:
            cls = operator.attrgetter(tag_suffix)(module)
        custom_constructor = getattr(cls, "from_yaml", None)
        if custom_constructor is not None:
            return custom_constructor(loader, node)
        return from_yaml_constructor(cls)(loader, node)

    return from_yaml
