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
"""

from .objects import (
    Data as Data,
)
from .objects import (
    DuplicateKey as DuplicateKey,
)
from .objects import (
    Module as Module,
)
from .objects import (
    OrderedDict as OrderedDict,
)
from .objects import (
    Output as Output,
)
from .objects import (
    Provider as Provider,
)
from .objects import (
    Resource as Resource,
)
from .objects import (
    Terraform as Terraform,
)
from .objects import (
    TFObject as TFObject,
)
from .objects import (
    Variable as Variable,
)
from .resource_collections import ResourceCollection as ResourceCollection
from .resource_collections import Variant as Variant
from .runtime_client import Client as Client
from .runtime_client import TerraformPy as TerraformPy

# add a couple shortcuts
compile = TFObject.compile
reset = TFObject.reset

__all__ = [
    "Data",
    "DuplicateKey",
    "Module",
    "OrderedDict",
    "Output",
    "Provider",
    "Resource",
    "Terraform",
    "TFObject",
    "Variable",
    "ResourceCollection",
    "Variant",
    "Client",
    "TerraformPy",
    "compile",
    "reset",
]
