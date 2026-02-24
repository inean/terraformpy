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

import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

from terraformpy import compile


def _load_module_from_path(file_path: Path) -> None:
    module_name = file_path.name[:-6]
    spec = spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to create import spec for {file_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)


def main() -> None:
    """Compile *.tf.py files and run Terraform"""
    cwd = Path.cwd()
    to_process = sorted(
        ent.name for ent in cwd.iterdir() if ent.name.endswith(".tf.py")
    )

    if len(to_process) == 0:
        print(f"terraformpy - Error loading config: No .tf.py files found in {cwd}")
        sys.exit(1)

    print(f"terraformpy - Processing: {', '.join(to_process)}")

    # all we need to do is import our files
    # the nature of resource declaration will register all of the objects for us to compile
    for filename in to_process:
        _load_module_from_path(cwd / filename)

    # now 'compile' everything that was registered, and write it out the tf.json file
    print("terraformpy - Writing main.tf.json")
    with open("main.tf.json", "w", encoding="utf-8") as fd:
        compiled: dict[str, Any] = compile()
        json.dump(compiled, fd, indent=4)
        fd.write("\n")

    if len(sys.argv) > 1:
        print(f"terraformpy - Running terraform: {' '.join(sys.argv[1:])}")
        # replace ourself with terraform
        os.execvp("terraform", ["terraform"] + sys.argv[1:])
