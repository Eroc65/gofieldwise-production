from pathlib import Path

import pytest

from agent_runtime.tool_executor import ToolExecutionError, ToolExecutor


def test_write_read_append_round_trip(tmp_path):
    executor = ToolExecutor(repo_root=tmp_path)

    write = executor.write_file("notes/test.txt", "hello")
    append = executor.append_file("notes/test.txt", " world")
    read = executor.read_file("notes/test.txt")

    assert write["ok"] is True
    assert append["ok"] is True
    assert read["content"] == "hello world"


def test_path_escape_blocked(tmp_path):
    executor = ToolExecutor(repo_root=tmp_path)
    with pytest.raises(ToolExecutionError):
        executor.read_file("../outside.txt")


def test_list_dir_and_search_text(tmp_path):
    base = Path(tmp_path)
    (base / "a").mkdir(parents=True, exist_ok=True)
    (base / "a" / "one.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (base / "a" / "two.py").write_text("print('alpha')\n", encoding="utf-8")

    executor = ToolExecutor(repo_root=tmp_path)
    listed = executor.list_dir("a")
    search = executor.search_text("alpha", path="a")

    assert any(x.endswith("a/one.txt") for x in listed["entries"])
    assert len(search["hits"]) == 2


def test_run_command_allowlist_and_blocklist(tmp_path):
    executor = ToolExecutor(repo_root=tmp_path)

    ok_result = executor.run_command("python --version", cwd=".")
    assert ok_result["tool_name"] == "run_command"

    with pytest.raises(ToolExecutionError):
        executor.run_command("rm -rf /", cwd=".")

    with pytest.raises(ToolExecutionError):
        executor.run_command("git reset --hard", cwd=".")
