import json

import pytest

from terraformpy import TFObject, cli


def test_main_without_tf_py_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "No .tf.py files found" in captured.out


def test_main_generates_main_tf_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tf.py").write_text(
        "from terraformpy import Resource\n"
        "Resource('aws_security_group', 'sg', ingress=['foo'])\n",
        encoding="utf-8",
    )

    cli.main()

    payload = json.loads((tmp_path / "main.tf.json").read_text(encoding="utf-8"))
    assert payload == {"resource": {"aws_security_group": {"sg": {"ingress": ["foo"]}}}}


def test_main_passthrough_to_terraform(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tf.py").write_text(
        "from terraformpy import Resource\n"
        "Resource('aws_security_group', 'sg', ingress=['foo'])\n",
        encoding="utf-8",
    )

    called: dict[str, object] = {}

    def fake_execvp(binary, argv):
        called["binary"] = binary
        called["argv"] = argv
        raise SystemExit(0)

    monkeypatch.setattr(cli.os, "execvp", fake_execvp)
    monkeypatch.setattr(cli.sys, "argv", ["terraformpy", "plan", "-input=false"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert called["binary"] == "terraform"
    assert called["argv"] == ["terraform", "plan", "-input=false"]


def test_load_module_from_path_raises_for_invalid_spec(tmp_path, monkeypatch):
    def fake_spec_from_file_location(name, path):
        return None

    monkeypatch.setattr(cli, "spec_from_file_location", fake_spec_from_file_location)

    with pytest.raises(RuntimeError):
        cli._load_module_from_path(tmp_path / "main.tf.py")

    TFObject.reset()
