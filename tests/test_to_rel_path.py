"""Tests for ``palinode.core.path_guard.to_rel_path``.

The historical MCP relativization (``file_path.rsplit("/palinode/", 1)``)
silently returned an absolute path unchanged whenever the configured memory
directory didn't happen to contain the literal substring ``/palinode/`` — the
common case for any custom install (``~/memory``, ``/srv/notes``, a
"second-brain" directory, etc.) — and mis-split when a directory segment
repeated (e.g. ``.../palinode/palinode/``).

``to_rel_path`` replaces the string-split with directory-based comparison
(``os.path.relpath`` against ``config.memory_dir``), so it works regardless
of what the memory directory is named. These tests exercise exactly the
configurations the old approach failed on.
"""
from __future__ import annotations

import ntpath
import os
from pathlib import Path

from palinode.core.config import config
from palinode.core.path_guard import to_rel_path


def test_rel_path_with_memory_dir_lacking_palinode_substring(monkeypatch, tmp_path):
    """The configuration every custom install actually has.

    No occurrence of "palinode" anywhere in the memory_dir path — the exact
    shape the old ``"/palinode/" in file_path`` guess silently failed on.
    """
    memory_dir = tmp_path / "second-brain"
    memory_dir.mkdir()
    monkeypatch.setattr(config, "memory_dir", str(memory_dir))

    abs_path = os.path.join(str(memory_dir), "decisions", "foo.md")
    assert to_rel_path(abs_path) == "decisions/foo.md"


def test_rel_path_with_repeated_directory_segment(monkeypatch, tmp_path):
    """A memory_dir whose own name repeats (``.../palinode/palinode``).

    The old ``rsplit("/palinode/", 1)`` split at the *first* occurrence and
    returned everything after it — including the second ``palinode/``
    segment, which is not part of the relative memory path at all.
    """
    memory_dir = tmp_path / "palinode" / "palinode"
    memory_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "memory_dir", str(memory_dir))

    abs_path = os.path.join(str(memory_dir), "insights", "bar.md")
    assert to_rel_path(abs_path) == "insights/bar.md"


def test_rel_path_with_default_palinode_dir_name(monkeypatch, tmp_path):
    """Sanity check: the historically-common ``~/palinode`` layout still works."""
    memory_dir = tmp_path / "palinode"
    memory_dir.mkdir()
    monkeypatch.setattr(config, "memory_dir", str(memory_dir))

    abs_path = os.path.join(str(memory_dir), "people", "alice.md")
    assert to_rel_path(abs_path) == "people/alice.md"


def test_rel_path_passes_through_already_relative_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "memory_dir", str(tmp_path))
    assert to_rel_path("decisions/foo.md") == "decisions/foo.md"


def test_rel_path_normalizes_already_relative_backslash_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "memory_dir", str(tmp_path))
    assert to_rel_path(r"decisions\foo.md") == "decisions/foo.md"
    assert to_rel_path(r"decisions\nested\bar.md") == "decisions/nested/bar.md"


def test_rel_path_passes_through_empty_string(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "memory_dir", str(tmp_path))
    assert to_rel_path("") == ""


def test_rel_path_falls_back_unchanged_when_outside_memory_dir(monkeypatch, tmp_path):
    """A genuinely-external absolute path is not silently rewritten into a
    misleading ``../`` relative path — it's returned unchanged, matching the
    old fallback's "leave it alone" behaviour for a path it can't relativize."""
    memory_dir = tmp_path / "second-brain"
    memory_dir.mkdir()
    monkeypatch.setattr(config, "memory_dir", str(memory_dir))

    outside = str(tmp_path / "elsewhere" / "file.md")
    assert to_rel_path(outside) == outside


def test_rel_path_accepts_explicit_base_dir_override(tmp_path):
    """The optional ``base_dir`` kwarg bypasses ``config.memory_dir`` entirely."""
    base = tmp_path / "custom-base"
    base.mkdir()
    abs_path = os.path.join(str(base), "research", "note.md")
    assert to_rel_path(abs_path, base_dir=str(base)) == "research/note.md"


def test_rel_path_supports_pathlike_inputs(tmp_path):
    """``os.PathLike`` / ``pathlib.Path`` inputs are accepted for file_path and base_dir."""
    memory_dir = tmp_path / "second-brain"
    memory_dir.mkdir()
    sub_path = memory_dir / "decisions" / "foo.md"

    # Absolute Path
    assert to_rel_path(sub_path, base_dir=memory_dir) == "decisions/foo.md"
    # Relative Path
    assert to_rel_path(Path("decisions/foo.md")) == "decisions/foo.md"


def test_rel_path_windows_semantics_with_ntpath(monkeypatch):
    """Verify Windows backslash paths normalize to POSIX forward slashes across all runners."""
    monkeypatch.setattr("palinode.core.path_guard.os.path", ntpath)

    base = r"C:\Users\test\memory"
    # In-tree path converts backslashes to forward slashes
    target = r"C:\Users\test\memory\projects\test.md"
    assert to_rel_path(target, base_dir=base) == "projects/test.md"

    # External path returns unchanged
    outside = r"C:\other\outside.md"
    assert to_rel_path(outside, base_dir=base) == outside

    # Cross-drive path returns unchanged
    cross_drive = r"D:\memory\projects\test.md"
    assert to_rel_path(cross_drive, base_dir=base) == cross_drive
