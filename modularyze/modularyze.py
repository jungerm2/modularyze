"""Main module."""
import hashlib
import json
import operator
import os
import warnings

import ruamel.yaml
import ruamel.yaml.constructor
import ruamel.yaml.error
from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    Template,
    select_autoescape,
)
from ruamel.yaml import MappingNode, SafeConstructor, ScalarNode, SequenceNode

from modularyze.construct import from_yaml_constructor, from_yaml_multi_constructor
from modularyze.utils import is_class, is_local, is_public


class ConfBuilder:
    """This configuration builder works with a jinja2 templated yaml
    file. It first renders the template, then parses the yaml file.

    It can be used to directly instantiate almost any object, provided
    that it's type has been registered first.
    """

    def __init__(self, yaml=None, attr_sep="."):
        self.yaml = yaml if yaml else ruamel.yaml.YAML(typ="safe")
        self.attr_sep = attr_sep
        self.registered_callables = {}
        self.registered_multi_callables = {}

    @staticmethod
    def _get_template(spec, root_path=None):
        if isinstance(spec, str):
            if os.path.isfile(os.path.join(root_path or "", spec)):
                return ConfBuilder._template_from_file(spec, root_path=root_path)
        return ConfBuilder._template_from_document(spec, root_path=root_path)

    @staticmethod
    def _template_from_file(conf_file, root_path=None):
        if root_path is None:
            root_path = os.path.dirname(conf_file)
            conf_file = os.path.basename(conf_file)
        env = Environment(
            loader=FileSystemLoader(root_path),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )
        template = env.get_template(conf_file)
        return template

    @staticmethod
    def _template_from_document(document, root_path=None):
        if root_path:
            env = Environment(
                loader=FileSystemLoader(root_path),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
                undefined=StrictUndefined,
            )
            template = env.from_string(document)
            return template
        return Template(document)

    @staticmethod
    def _vanilla_yaml_constructors():
        """The default parser created by `ruamel.yaml.YAML` inherits any
        constructors that were added since the last kernel restart. This is
        due to the odd fact that these constructors are a class method instead
        of an instance method.
        This method returns the default constructors added to the SafeConstructor
        class when first initialized. Return a dict that maps the tag to it's constructor.
        """
        default_types = [
            "null",
            "bool",
            "int",
            "float",
            "binary",
            "timestamp",
            "omap",
            "pairs",
            "set",
            "str",
            "seq",
            "map",
        ]
        default_constructors = {
            f"tag:yaml.org,2002:{t}": getattr(SafeConstructor, f"construct_yaml_{t}")
            for t in default_types
        }
        default_constructors.update({None: SafeConstructor.construct_undefined})
        return default_constructors

    @staticmethod
    def _vanilla_yaml_multi_constructors():
        """This method returns the default multi-constructors added to the SafeConstructor
        class when first initialized (there are none).
        See :meth:`_vanilla_yaml_constructors` for more."""
        return {}

    def _reset_yaml_constructors(self):
        self.yaml.Constructor.yaml_constructors = self._vanilla_yaml_constructors()
        self.yaml.Constructor.yaml_multi_constructors = (
            self._vanilla_yaml_multi_constructors()
        )

    @property
    def constructors(self):
        """Return registered constructors and multi-constructors"""
        return {
            "constructors": self.yaml.Constructor.yaml_constructors,
            "multi_constructors": self.yaml.Constructor.yaml_multi_constructors,
        }

    @staticmethod
    def default_tag_name(obj):
        """The default tag name for an object is simply the
        object's name prefixed by an exclamation point"""
        return f"!{obj.__name__}"

    @staticmethod
    def get_data(loader, node):
        """Convert node to it's builtin representation
            ScalarNode -> one of bool, int, float, etc...
            SequenceNode -> list, tuple, ...
            MappingNode -> dictionary, omap, ...
        """
        if isinstance(node, ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, SequenceNode):
            return loader.construct_sequence(node, deep=True)
        if isinstance(node, MappingNode):
            return loader.construct_mapping(node, deep=True)
        raise ruamel.yaml.constructor.ConstructorError(
            f"Type of node not understood. Received {type(node)} but expected "
            f"`ScalarNode`, `SequenceNode`, `MappingNode` or subtype"
        )

    def vanilla_load(self, document, ignore_unknown=False):
        """Reset the yaml loader by temporarily clearing it's constructors, load the
        document, then add back the constructors.
        If `ignore_unknown`, unrecognized tags will be replaced by None, otherwise they will
        be converted to their text representation.

        *Note:* This relies on monkey-patching the yaml parser, so use with care. See code for more."""
        # Temporarily reset the constructors to their defaults, add a
        # wildcard constructor in order to not actually instantiate foreign objects

        # Capture custom constructors
        registered_constructors = self.yaml.Constructor.yaml_constructors
        registered_multi_constructors = self.yaml.Constructor.yaml_multi_constructors

        # Reset them to their defaults
        self._reset_yaml_constructors()

        # Add wildcard constructor to ignore unknown tags or turn them to strings
        def wildcard_constructor(loader, node):
            if not ignore_unknown:
                return {node.tag: self.get_data(loader, node)}

        self.yaml.Constructor.add_constructor(None, wildcard_constructor)

        # Parse document to get an un-instantiated/normalized one
        normalized_conf = self.yaml.load(document)

        # Restore all constructors
        self.yaml.Constructor.yaml_constructors = registered_constructors
        self.yaml.Constructor.yaml_multi_constructors = registered_multi_constructors

        return normalized_conf

    @staticmethod
    def _warn_override(new_callables, old_callables, warning_msg):
        updated_tags_from_named = set(new_callables.keys()) & set(old_callables.keys())

        for tag in updated_tags_from_named:
            src, dst = old_callables[tag], new_callables[tag]
            if src != dst:
                msg = warning_msg.format(tag=tag, src=src, dst=dst)
                warnings.warn(msg, RuntimeWarning)

    def _validate_callables(self, *callables, warning_msg=None, **named_callables):
        """Name all callables with unspecified tags, merge with name callables, and
        warn if any un-named callables clobber the named ones."""
        default_callables = {self.default_tag_name(cls): cls for cls in callables}

        all_callables = {}
        all_callables.update(default_callables)
        all_callables.update(
            {k.rstrip(self.attr_sep): v for k, v in named_callables.items()}
        )

        if warning_msg is None:
            warning_msg = (
                "Constructor for YAML tag '{tag}' overridden from {src} to {dst}"
            )

        # Check for overrides of callables by named_callables
        self._warn_override(named_callables, default_callables, warning_msg)

        # Check for overrides of existing callables by new callables
        self._warn_override(all_callables, self.registered_callables, warning_msg)

        # Check for overrides of existing multi-callables by new callables
        self._warn_override(all_callables, self.registered_multi_callables, warning_msg)

        return all_callables

    def register_constructors(self, *callables, **named_callables):
        """For an object to be instantiated, or a function to be called,
        when loading the configuration from yaml, it needs to be first
        registered by the builder. This registration creates a default
        constructor for that callable that yaml will use when it parses
        that callable's tag.

        A tag can either be specified, or if left out, a default tag will
        be used (see :meth:`default_tag_name`).

        Args:
            callables: classes or functions to register_constructors with a default tag
            named_callables: other callables with specified tag names
        """
        all_callables = self._validate_callables(*callables, **named_callables)
        self.registered_callables.update(all_callables)

        # Register callables
        for tag_name, cls in all_callables.items():
            if getattr(cls, "from_yaml", None) is None:
                self.yaml.Constructor.add_constructor(
                    tag_name, from_yaml_constructor(cls)
                )
            else:
                self.yaml.register_class(cls)

    def register_constructors_from_modules(
        self, *modules, filter_funcs=None, **named_modules
    ):
        """It's often helpful to `register_constructors` from a module.
        This method registers all attributes of a given module that
        satisfy the filter functions, prepending a given prefix to
        the autogenerated tag name.

        This is similar to using `from package import *` as it will clutter
        the namespace and probably over-`register_constructors`. It is often
        best to use `register_multi_constructors_from_modules`.

        *Note:* This might fail if the `__name__` attribute is not set on either an
        unnamed module, or any sub-module/callable.

        Args:
            modules: List of modules to register implicitly. These modules will be
                registered using an inferred tag-prefix of '!<module name>'.
            named_modules: Dictionary of tag-prefixes -> modules to register explicitly.
                The modules passed as kwargs will be registered with the key as their tag.
            filter_funcs:
                these provide a way to limit registration by filtering
                out any callables that don't meet a requirement. By
                default any private attribute or non-class attribute
                is not registered.
        """
        all_callables = self._validate_callables(*modules, **named_modules)

        filter_funcs = filter_funcs if filter_funcs else [is_class, is_public, is_local]

        for prefix, module in all_callables.items():
            prefix = prefix.rstrip(self.attr_sep)
            attrs = [
                (attr_name, getattr(module, attr_name)) for attr_name in dir(module)
            ]
            named_callables = {
                f"{prefix}{self.attr_sep}{attr.__name__}": attr
                for attr_name, attr in attrs
                if all(f(attr_name, attr, module) for f in filter_funcs)
            }
            self.register_constructors(**named_callables)

    def register_multi_constructors(self, *callables, **named_callables):
        """This registration creates a default multi-constructor for the given callables.

        A tag prefix can either be specified, or if left out, a default tag prefix will
        be used (see :meth:`default_tag_name`).

        Args:
            callables: classes or functions to register a multi-constructors with a default tag prefix
            named_callables: other callables with specified tag prefix
        """
        warning_msg = (
            "Multi-constructor for YAML tag '{tag}' overridden from {src} to {dst}"
        )
        all_callables = self._validate_callables(
            *callables, warning_msg=warning_msg, **named_callables
        )

        self.registered_multi_callables.update(all_callables)

        # Register multi-callables
        for prefix, module in all_callables.items():
            self.yaml.Constructor.add_multi_constructor(
                prefix, from_yaml_multi_constructor(module, attr_sep=self.attr_sep)
            )

    def register_multi_constructors_from_modules(self, *modules, **named_modules):
        """This method registers modules as multi-constructors enabling
        submodules to be accessed dynamically and lazy loaded.

        This is favored over `register_constructors_from_modules` as it
        only adds one multi-constructor per module instead of numerous single
        use constructors per module.

        Args:
            modules: List of modules to register implicitly. These modules will be
                registered using an inferred tag-prefix of '!<module name>'.
                Note that this might fail if the `__name__` attribute is not set.
            named_modules: Dictionary of tag-prefixes -> modules to register explicitly.
                The modules passed as kwargs will be registered with the key as their tag.
        """
        self.register_multi_constructors(*modules, **named_modules)

    def render(self, spec, context=None, root_path=None):
        """Method responsible for rendering the config template. If context
        is a valid (simple) yaml file then it will be used as context for
        jinja's rendering, otherwise context should be a dictionary or object
        that can be unpacked using the double-star operator (**).

        Args:
            spec: config path or string
            context: context to pass to templating engine
            root_path: path of config directory (only needed if config is multi-file)

        Returns:
            A rendered template, which is the fully formed YAML config file.
        """
        if isinstance(context, str):
            if os.path.isfile(context):
                with open(context) as f:
                    context = f.read()
            context = self.vanilla_load(context, ignore_unknown=True)
        template = self._get_template(spec, root_path=root_path)
        return template.render(**({} if context is None else context))

    def normalize(self, spec, sort_keys=False, raw=False, context=None, root_path=None):
        """Get the config pre-initialization of members as a normalized representation.

        Args: Same as :meth:`render`

        Returns: Normalized representation of configuration as a string.
        """
        document = self.render(spec, context=context, root_path=root_path)
        normalized_conf = self.vanilla_load(document, ignore_unknown=False)
        if raw:
            return normalized_conf
        return json.dumps(normalized_conf, indent=2, sort_keys=sort_keys)

    def load(self, document):
        """Load and instantiate the rendered config (full-YAML document).

        Args: document: YAML document as a string.

        Returns: Config object (dict, list, etc...)
        """
        try:
            return self.yaml.load(document)
        except ruamel.yaml.constructor.ConstructorError:
            raise
        except ruamel.yaml.error.MarkedYAMLError as e:
            line = operator.attrgetter("problem_mark.line")(e)
            line = line or operator.attrgetter("context_mark.line")(e)
            column = operator.attrgetter("problem_mark.column")(e)
            column = column or operator.attrgetter("context_mark.column")(e)

            if line and column:
                line, column = int(line), int(column)
                snippet = document.splitlines()
                snippet = snippet[line - 3 : line + 4]
                snippet = "\n".join(snippet)
                note = getattr(e, "note")
                note = note if note else ""
                note += f"\n\nError occurred around here:\n\n{snippet}"
                e.note = note
            raise

    def hash(self, spec, context=None, root_path=None):
        """Hash a config. This hash will depend on the spec (conf string or file)
        as well as any context it depends on.

        For the hash to be computed, the config is first normalized (see :meth:`normalize`)
        as a key-sorted, json-dumped string and then hashed using the SHA3-256 algorithm.

        Args:
            Same as :meth:`render`

        Returns:
            The config's unique hash as an int
        """
        hash_obj = hashlib.sha3_256(
            self.normalize(
                spec, sort_keys=True, raw=False, context=context, root_path=root_path
            ).encode("utf-8")
        )
        return int.from_bytes(hash_obj.digest(), "big")

    def build(self, spec, context=None, root_path=None):
        """Build the final configuration by first rendering the spec as a template
        and then building the resulting YAML document.

        Args:
            Same as :meth:`render`

        Returns: Config object (dict, list, etc...)
        """
        document = self.render(spec, context=context, root_path=root_path)
        return self.load(document)

    def __call__(self, *args, **kwargs):
        """Alias of :meth:`build`"""
        return self.build(*args, **kwargs)
