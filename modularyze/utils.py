def is_class(attr_name, attr, module):
    return isinstance(attr, type)


def is_public(attr_name, attr, module):
    return not attr_name.startswith("_")


def is_local(attr_name, attr, module):
    all_attrs = getattr(attr, "__all__", False)
    if all_attrs:
        return attr_name in all_attrs
    return attr.__module__.startswith(module.__package__)
