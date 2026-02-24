from types import SimpleNamespace
from typing import Any

from terraformpy import Client, TerraformPy


def _install_run_spy(monkeypatch):
    calls: list[dict[str, Any]] = []

    def fake_run(cmd, cwd, capture_output, text, check):
        calls.append(
            {
                "cmd": cmd,
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "check": check,
            }
        )
        return SimpleNamespace(returncode=0, stdout='{"x":{"value":"y"}}\n')

    monkeypatch.setattr("terraformpy.runtime_client.subprocess.run", fake_run)
    return calls


def test_constructor_accepts_no_kwargs():
    client = Client()
    assert isinstance(client, Client)


def test_constructor_accepts_workdir_variants(monkeypatch, tmp_path):
    calls = _install_run_spy(monkeypatch)

    Client(working_dir=str(tmp_path / "a")).plan()
    Client(chdir=str(tmp_path / "b")).plan()
    Client(cwd=str(tmp_path / "c")).plan()

    assert calls[0]["cwd"] == tmp_path / "a"
    assert calls[1]["cwd"] == tmp_path / "b"
    assert calls[2]["cwd"] == tmp_path / "c"


def test_plan_call_shapes(monkeypatch):
    calls = _install_run_spy(monkeypatch)
    client = Client()

    assert client.plan(var_file="vars.tfvars", out="tfplan", input=False, no_color=True) == 0
    assert client.plan(var_file="vars.tfvars", out="tfplan") == 0
    assert client.plan("-var-file=vars.tfvars", "-out=tfplan", "-input=false", "-no-color") == 0

    assert calls[0]["cmd"] == [
        "terraform",
        "plan",
        "-var-file=vars.tfvars",
        "-out=tfplan",
        "-input=false",
        "-no-color",
    ]
    assert calls[1]["cmd"] == ["terraform", "plan", "-var-file=vars.tfvars", "-out=tfplan"]
    assert calls[2]["cmd"] == [
        "terraform",
        "plan",
        "-var-file=vars.tfvars",
        "-out=tfplan",
        "-input=false",
        "-no-color",
    ]


def test_apply_call_shapes(monkeypatch):
    calls = _install_run_spy(monkeypatch)
    client = Client()

    assert client.apply(plan="tfplan", auto_approve=True, input=False, no_color=True) == 0
    assert client.apply(plan="tfplan", auto_approve=True) == 0
    assert client.apply("tfplan") == 0
    assert client.apply("-auto-approve", "tfplan") == 0

    assert calls[0]["cmd"] == [
        "terraform",
        "apply",
        "-auto-approve",
        "-input=false",
        "-no-color",
        "tfplan",
    ]
    assert calls[1]["cmd"] == ["terraform", "apply", "-auto-approve", "tfplan"]
    assert calls[2]["cmd"] == ["terraform", "apply", "tfplan"]
    assert calls[3]["cmd"] == ["terraform", "apply", "-auto-approve", "tfplan"]


def test_destroy_call_shapes(monkeypatch):
    calls = _install_run_spy(monkeypatch)
    client = Client()

    assert (
        client.destroy(
            var={"vm_name": "vm-1"},
            auto_approve=True,
            input=False,
            no_color=True,
        )
        == 0
    )
    assert client.destroy(var="vm_name=vm-1", auto_approve=True) == 0
    assert client.destroy("-auto-approve", "-var=vm_name=vm-1") == 0

    assert calls[0]["cmd"] == [
        "terraform",
        "destroy",
        "-auto-approve",
        "-var=vm_name=vm-1",
        "-input=false",
        "-no-color",
    ]
    assert calls[1]["cmd"] == [
        "terraform",
        "destroy",
        "-auto-approve",
        "-var=vm_name=vm-1",
    ]
    assert calls[2]["cmd"] == ["terraform", "destroy", "-auto-approve", "-var=vm_name=vm-1"]


def test_output_call_shapes(monkeypatch):
    calls = _install_run_spy(monkeypatch)
    client = Client()

    assert client.output(json=True) == {"x": {"value": "y"}}
    assert client.output("-json") == {"x": {"value": "y"}}
    assert client.output() == {"x": {"value": "y"}}

    assert calls[0]["cmd"] == ["terraform", "output", "-json"]
    assert calls[1]["cmd"] == ["terraform", "output", "-json"]
    assert calls[2]["cmd"] == ["terraform", "output", "-json"]


def test_alias_export():
    client = TerraformPy()
    assert isinstance(client, Client)
