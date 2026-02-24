import json
import subprocess
from pathlib import Path
from typing import Any


class Client:
    def __init__(
        self,
        *,
        working_dir: str | None = None,
        chdir: str | None = None,
        cwd: str | None = None,
    ) -> None:
        selected_cwd = working_dir or chdir or cwd
        self._cwd = Path(selected_cwd) if selected_cwd is not None else None

    def init(self, *args: str, **kwargs: Any) -> int:
        cmd = ["init"]
        cmd.extend(args)
        cmd.extend(self._common_flags(kwargs))
        return self._run_returncode(cmd)

    def plan(self, *args: str, **kwargs: Any) -> int:
        cmd = ["plan"]
        if len(args) > 0:
            cmd.extend(args)
        else:
            var_file = kwargs.pop("var_file", None)
            out = kwargs.pop("out", None)
            if var_file is not None:
                cmd.append(f"-var-file={var_file}")
            if out is not None:
                cmd.append(f"-out={out}")
            cmd.extend(self._common_flags(kwargs))
        return self._run_returncode(cmd)

    def apply(self, *args: str, **kwargs: Any) -> int:
        cmd = ["apply"]
        if len(args) > 0:
            cmd.extend(args)
        else:
            plan = kwargs.pop("plan", None)
            auto_approve = kwargs.pop("auto_approve", None)
            if auto_approve:
                cmd.append("-auto-approve")
            cmd.extend(self._common_flags(kwargs))
            if plan is not None:
                cmd.append(str(plan))
        return self._run_returncode(cmd)

    def destroy(self, *args: str, **kwargs: Any) -> int:
        cmd = ["destroy"]
        if len(args) > 0:
            cmd.extend(args)
        else:
            var = kwargs.pop("var", None)
            auto_approve = kwargs.pop("auto_approve", None)
            if auto_approve:
                cmd.append("-auto-approve")
            if isinstance(var, dict):
                for key, value in var.items():
                    cmd.append(f"-var={key}={value}")
            elif var is not None:
                cmd.append(f"-var={var}")
            cmd.extend(self._common_flags(kwargs))
        return self._run_returncode(cmd)

    def output(self, *args: str, **kwargs: Any) -> dict[str, Any] | int:
        cmd = ["output"]
        if len(args) > 0:
            cmd.extend(args)
        if kwargs.pop("json", False) and "-json" not in cmd:
            cmd.append("-json")
        if "-json" not in cmd:
            cmd.append("-json")

        proc = self._run_process(cmd)
        if proc.returncode != 0:
            return proc.returncode
        stdout = proc.stdout.strip()
        return json.loads(stdout) if stdout else {}

    def _common_flags(self, kwargs: dict[str, Any]) -> list[str]:
        flags: list[str] = []
        input_value = kwargs.pop("input", None)
        if input_value is not None:
            flags.append(f"-input={str(bool(input_value)).lower()}")
        if kwargs.pop("no_color", None):
            flags.append("-no-color")
        return flags

    def _run_returncode(self, cmd: list[str]) -> int:
        return self._run_process(cmd).returncode

    def _run_process(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["terraform", *cmd],
            cwd=self._cwd,
            capture_output=True,
            text=True,
            check=False,
        )


TerraformPy = Client
