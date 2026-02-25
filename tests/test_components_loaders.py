"""
Tests for MarkdownLoader, PlainTextLoader, DirectoryLoader, DocumentLoaderPort — 8 cases.

Uses pytest tmp_path fixture to create temporary files in isolation.
"""

from __future__ import annotations

import pytest

from lang2sql.components.loaders import DirectoryLoader, MarkdownLoader, PlainTextLoader
from lang2sql.core.ports import DocumentLoaderPort


# ---------------------------------------------------------------------------
# 1. MarkdownLoader — single file: TextDocument fields are correct
# ---------------------------------------------------------------------------


def test_markdown_loader_single_file(tmp_path):
    md_file = tmp_path / "revenue.md"
    md_file.write_text("# Revenue Definition\n\nRevenue is net sales.", encoding="utf-8")

    docs = MarkdownLoader().load(str(md_file))

    assert len(docs) == 1
    doc = docs[0]
    assert doc["id"] == "revenue"
    assert doc["title"] == "Revenue Definition"
    assert "Revenue is net sales" in doc["content"]
    assert doc["source"] == str(md_file)


# ---------------------------------------------------------------------------
# 2. MarkdownLoader — directory: returns one doc per .md file
# ---------------------------------------------------------------------------


def test_markdown_loader_directory(tmp_path):
    (tmp_path / "a.md").write_text("# A\ncontent a", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B\ncontent b", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("plain text", encoding="utf-8")  # ignored

    docs = MarkdownLoader().load(str(tmp_path))

    assert len(docs) == 2
    ids = {d["id"] for d in docs}
    assert ids == {"a", "b"}


# ---------------------------------------------------------------------------
# 3. MarkdownLoader — title extracted from first # heading
# ---------------------------------------------------------------------------


def test_markdown_loader_title_from_heading(tmp_path):
    md_file = tmp_path / "doc.md"
    md_file.write_text("Some intro\n# My Title\nBody text.", encoding="utf-8")

    docs = MarkdownLoader().load(str(md_file))

    # The first # heading (even if not the first line) is used as title
    assert docs[0]["title"] == "My Title"


# ---------------------------------------------------------------------------
# 4. MarkdownLoader — no heading → title falls back to filename stem
# ---------------------------------------------------------------------------


def test_markdown_loader_no_heading(tmp_path):
    md_file = tmp_path / "quarterly_report.md"
    md_file.write_text("Just some content without a heading.", encoding="utf-8")

    docs = MarkdownLoader().load(str(md_file))

    assert docs[0]["title"] == "quarterly_report"


# ---------------------------------------------------------------------------
# 5. PlainTextLoader — single file: content is correct
# ---------------------------------------------------------------------------


def test_plaintext_loader_single_file(tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("line one\nline two\n", encoding="utf-8")

    docs = PlainTextLoader().load(str(txt_file))

    assert len(docs) == 1
    doc = docs[0]
    assert doc["id"] == "notes"
    assert doc["title"] == "notes"
    assert "line one" in doc["content"]
    assert doc["source"] == str(txt_file)


# ---------------------------------------------------------------------------
# 6. DirectoryLoader — dispatches by extension
# ---------------------------------------------------------------------------


def test_directory_loader_dispatches_by_extension(tmp_path):
    (tmp_path / "guide.md").write_text("# Guide\nMarkdown content.", encoding="utf-8")
    (tmp_path / "data.txt").write_text("plain text content", encoding="utf-8")

    docs = DirectoryLoader(str(tmp_path)).load()

    ids = {d["id"] for d in docs}
    assert "guide" in ids   # loaded by MarkdownLoader
    assert "data" in ids    # loaded by PlainTextLoader


# ---------------------------------------------------------------------------
# 7. DirectoryLoader — skips unknown extensions
# ---------------------------------------------------------------------------


def test_directory_loader_skips_unknown_extension(tmp_path):
    (tmp_path / "script.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "data.csv").write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    (tmp_path / "readme.md").write_text("# Readme\ncontent", encoding="utf-8")

    docs = DirectoryLoader(str(tmp_path)).load()

    ids = {d["id"] for d in docs}
    assert "readme" in ids        # .md is loaded
    assert "script" not in ids    # .py is skipped
    assert "data" not in ids      # .csv is skipped (not in default loaders)


# ---------------------------------------------------------------------------
# 8. Protocol check — MarkdownLoader and PlainTextLoader satisfy DocumentLoaderPort
# ---------------------------------------------------------------------------


def test_document_loader_port_protocol():
    assert isinstance(MarkdownLoader(), DocumentLoaderPort)
    assert isinstance(PlainTextLoader(), DocumentLoaderPort)
