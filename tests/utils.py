#####################################################################
#                          Dummy Callables                          #
#####################################################################


class Foo:
    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs


class Bar:
    pass


class Dice:
    def __init__(self, a, b):
        self.a, self.b = a, b

    def __repr__(self):
        return f"Dice({self.a}, {self.b})"

    @classmethod
    def from_yaml(cls, loader, node):
        value = loader.construct_scalar(node)
        a, b = map(int, value.split("d"))
        return cls(a, b)
