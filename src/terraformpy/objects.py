"""
Copyright 2019 NerdWallet

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Terraform "objects"

This module provides a set of classes that can be used to build Terraform
configurations in a (mostly) declarative way, while also leveraging Python to
add some functional aspects to automate repetitive HCL tasks.
"""

from collections import OrderedDict as OrderedDictImpl
from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import Any, ClassVar, cast

from schematics.types import compound

from .resource_collections import Variant

JsonDict = dict[str, Any]
Hook = Callable[[JsonDict], JsonDict]


def recursive_update(dest: JsonDict, source: Mapping[str, Any]) -> JsonDict:
    """Like ``dict.update``, but recursive."""
    for key, val in source.items():
        if isinstance(val, Mapping):
            recurse = recursive_update(dest.get(key, {}), val)
            dest[key] = recurse
        else:
            dest[key] = val
    return dest


class DuplicateKey(str):
    """A string subtype that keeps duplicated keys distinct in dicts."""

    _next_hash: ClassVar[defaultdict[str, int]] = defaultdict(lambda: 0)

    def __new__(cls, key: str) -> "DuplicateKey":
        inst = super().__new__(cls, key)
        inst._hash = hash((key, DuplicateKey._next_hash[key]))
        DuplicateKey._next_hash[key] += 1
        return inst

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DuplicateKey) and self._hash == other._hash

    def __lt__(self, other: str) -> bool:
        if isinstance(other, DuplicateKey):
            return self._hash < other._hash
        return cast(bool, super().__lt__(other))

    def __le__(self, other: str) -> bool:
        if isinstance(other, DuplicateKey):
            return self._hash <= other._hash
        return cast(bool, super().__le__(other))

    def __gt__(self, other: str) -> bool:
        if isinstance(other, DuplicateKey):
            return self._hash > other._hash
        return cast(bool, super().__gt__(other))

    def __ge__(self, other: str) -> bool:
        if isinstance(other, DuplicateKey):
            return self._hash >= other._hash
        return cast(bool, super().__ge__(other))


class OrderedDict(compound.DictType):
    """A Schematics DictType that preserves insertion order."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.native_type = OrderedDictImpl

    def convert(self, value: Mapping[str, Any], context: Any = None) -> OrderedDictImpl:
        temp_data = super().convert(value, context)
        data: OrderedDictImpl[str, Any] = OrderedDictImpl()
        for key in value.keys():
            data[key] = temp_data[key]
        return data


class TFObject:
    _instances: ClassVar[list["TFObject"] | None] = None
    _frozen: ClassVar[bool] = False
    _hooks: ClassVar[dict[str, list[Hook]] | None] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "TFObject":
        inst = super().__new__(cls)
        if cls._instances is None:
            cls._instances = [inst]
        else:
            cls._instances.append(inst)
        return inst

    @classmethod
    def add_hook(cls, object_type: str, hook: Hook) -> None:
        if TFObject._hooks is None:
            TFObject._hooks = {object_type: [hook]}
            return
        TFObject._hooks.setdefault(object_type, []).append(hook)

    @classmethod
    def reset(cls) -> None:
        def recursive_reset(klass: type[TFObject]) -> None:
            klass._instances = None
            for subclass in klass.__subclasses__():
                recursive_reset(subclass)

        recursive_reset(cls)
        TFObject._frozen = False
        TFObject._hooks = None

    @classmethod
    def compile(cls) -> JsonDict:
        TFObject._frozen = True

        def recursive_compile(klass: type[TFObject]) -> list[JsonDict]:
            results: list[JsonDict] = []
            for instance in klass._instances or []:
                output = instance.build()

                for object_type in output:
                    for hook in (TFObject._hooks or {}).get(object_type, []):
                        output = hook(output)

                results.append(output)

            for subclass in klass.__subclasses__():
                results.extend(recursive_compile(subclass))
            return results

        configs = recursive_compile(cls)

        result: JsonDict = {}
        for config in configs:
            result = recursive_update(result, config)
        return result

    def build(self) -> JsonDict:
        raise NotImplementedError


class Terraform(TFObject):
    """Represents Terraform configuration."""

    @classmethod
    def add_hook(cls, hook: Hook) -> None:
        TFObject.add_hook("terraform", hook)

    def __init__(self, _values: JsonDict | None = None, **kwargs: Any) -> None:
        self._values = _values or {}
        self._values.update(kwargs)

    def build(self) -> JsonDict:
        return {"terraform": self._values}


class NamedObject(TFObject):
    """Terraform object with a single name component (e.g. variable/output)."""

    TF_TYPE: ClassVar[str | None] = None

    @classmethod
    def add_hook(cls, object_name: str, hook: Callable[[JsonDict], JsonDict]) -> None:
        def named_hook(output: JsonDict) -> JsonDict:
            tf_type = cls.TF_TYPE
            if tf_type is None:
                return output
            for output_name in output[tf_type]:
                if output_name != object_name:
                    continue
                output[tf_type][output_name] = hook(output[tf_type][output_name])
            return output

        assert cls.TF_TYPE is not None
        TFObject.add_hook(cls.TF_TYPE, named_hook)

    def __init__(
        self, _name: str, _values: JsonDict | None = None, **kwargs: Any
    ) -> None:
        assert self.TF_TYPE is not None, (
            f"Bad programmer.  Set TF_TYPE on {self.__class__.__name__}"
        )

        self._name = _name
        self._values: JsonDict = _values or {}

        if Variant.CURRENT_VARIANT is None:
            self._values.update(kwargs)
        else:
            for name, value in kwargs.items():
                if not name.endswith("_variant"):
                    self._values[name] = value
                elif name == f"{Variant.CURRENT_VARIANT.name}_variant":
                    assert isinstance(value, dict)
                    self._values.update(value)

    def __setattr__(self, name: str, value: Any) -> None:
        if "_values" in self.__dict__ and name in self.__dict__["_values"]:
            self.__dict__["_values"][name] = value
        else:
            self.__dict__[name] = value

    def __getattr__(self, name: str) -> Any:
        if not TFObject._frozen and name in self._values:
            return self._values[name]
        raise AttributeError(
            f"{self.__class__.__name__}s does not provide attribute interpolation "
            "through attribute access!"
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._name == other._name
            and self._values == other._values
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def build(self) -> JsonDict:
        assert self.TF_TYPE is not None
        return {self.TF_TYPE: {self._name: self._values}}

    def __repr__(self) -> str:
        return f"{type(self)} {self._name}"


class TypedObjectAttr(str):
    """Wrapper returned for non-existent attributes on TypedObject instances."""

    def __new__(
        cls, terraform_name: str, name: str, item: str | int | None = None
    ) -> "TypedObjectAttr":
        obj = super().__new__(
            cls, f"${{{terraform_name}.{cls._name_with_index(name, item)}}}"
        )
        obj._terraform_name = terraform_name
        obj._name = name
        obj._item = item
        return obj

    @staticmethod
    def _name_with_index(name: str, item: str | int | None) -> str:
        if item is None:
            return name
        return f"{name}.{item}"

    def __getitem__(self, item: str | int) -> "TypedObjectAttr":
        return TypedObjectAttr(
            self._terraform_name, self._name_with_index(self._name, self._item), item
        )

    def __getattr__(self, item: str) -> "TypedObjectAttr":
        return TypedObjectAttr(
            self._terraform_name, self._name_with_index(self._name, self._item), item
        )


class TypedObject(NamedObject):
    """Terraform object with both a type and name (resource/data)."""

    @classmethod
    def add_hook(
        cls, object_type: str, hook: Callable[[str, JsonDict], JsonDict]
    ) -> None:
        def typed_hook(output: JsonDict) -> JsonDict:
            tf_type = cls.TF_TYPE
            if tf_type is None:
                return output
            for output_type in output[tf_type]:
                if output_type != object_type:
                    continue
                for object_id in output[tf_type][object_type]:
                    output[tf_type][object_type][object_id] = hook(
                        object_id, output[tf_type][object_type][object_id]
                    )
            return output

        assert cls.TF_TYPE is not None
        TFObject.add_hook(cls.TF_TYPE, typed_hook)

    def __init__(self, _type: str, _name: str, **kwargs: Any) -> None:
        super().__init__(_name, **kwargs)
        self._type = _type

        if (
            "provider" not in kwargs
            and Provider.CURRENT_PROVIDER is not None
            and Provider.CURRENT_PROVIDER._name == self._type.split("_")[0]
        ):
            self._values["provider"] = Provider.CURRENT_PROVIDER.as_provider()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, TypedObject)
            and super().__eq__(other)
            and self._type == other._type
        )

    @property
    def terraform_name(self) -> str:
        return ".".join([self._type, self._name])

    def interpolated(self, name: str) -> Any:
        try:
            TFObject._frozen = True
            return getattr(self, name)
        finally:
            TFObject._frozen = False

    def __getattr__(self, name: str) -> Any:
        if not TFObject._frozen and name in self._values:
            return self._values[name]
        return TypedObjectAttr(self.terraform_name, name)

    def build(self) -> JsonDict:
        assert self.TF_TYPE is not None
        return {self.TF_TYPE: {self._type: {self._name: self._values}}}

    def __repr__(self) -> str:
        return f"{type(self)} {self._type} {self._name}"

    def __str__(self) -> str:
        return self.__repr__()


class Provider(NamedObject):
    """Represents a Terraform provider configuration."""

    TF_TYPE = "provider"
    CURRENT_PROVIDER: ClassVar["Provider | None"] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._key = DuplicateKey(self._name)

    def __enter__(self) -> "Provider":
        assert self._values["alias"], (
            "Providers must have an alias to be used as a context manager!"
        )
        self._previous_provider = Provider.CURRENT_PROVIDER
        Provider.CURRENT_PROVIDER = self
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        Provider.CURRENT_PROVIDER = self._previous_provider

    def as_provider(self) -> str:
        return ".".join([self._name, self._values["alias"]])

    def build(self) -> JsonDict:
        assert self.TF_TYPE is not None
        return {self.TF_TYPE: {self._key: self._values}}


class Variable(NamedObject):
    """Represents a Terraform variable."""

    TF_TYPE = "variable"

    def __repr__(self) -> str:
        return f"${{var.{self._name}}}"

    def __str__(self) -> str:
        return self.__repr__()


class Output(NamedObject):
    """Represents a Terraform output."""

    TF_TYPE = "output"


class Module(NamedObject):
    """Represents a Terraform module."""

    TF_TYPE = "module"


class Data(TypedObject):
    """Represents a Terraform data source."""

    TF_TYPE = "data"

    @property
    def terraform_name(self) -> str:
        return ".".join(["data", super().terraform_name])


class Resource(TypedObject):
    """Represents a Terraform resource."""

    TF_TYPE = "resource"
