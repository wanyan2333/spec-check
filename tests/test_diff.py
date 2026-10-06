from spec_check.diff import is_test_file, parse_diff
from tests.conftest import DIFF


def test_parses_files_and_sides():
    files = parse_diff(DIFF)
    assert set(files) == {"app.py", "test_app.py"}
    app = files["app.py"]
    assert "    todos.pop(todo_id, None)" in app.added_lines
    assert "    return todos[todo_id]" in app.new_lines  # context line
    assert "    todos.pop(todo_id, None)" not in app.old_lines


def test_removed_line_starting_with_dashes_is_not_a_header():
    diff = (
        "--- a/notes.py\n+++ b/notes.py\n@@ -1,2 +1,2 @@\n"
        "--- old comment line\n+x = 1\n keep = True\n"
    )
    files = parse_diff(diff)
    assert list(files) == ["notes.py"]
    assert files["notes.py"].old_lines == ["-- old comment line", "keep = True"]
    assert files["notes.py"].new_lines == ["x = 1", "keep = True"]


def test_new_and_deleted_files():
    diff = (
        "--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+print('hi')\n"
        "--- a/gone.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-print('bye')\n"
    )
    files = parse_diff(diff)
    assert files["new.py"].added_lines == ["print('hi')"]
    assert files["gone.py"].old_lines == ["print('bye')"]


def test_is_test_file():
    assert is_test_file("test_app.py")
    assert is_test_file("pkg/tests/helpers.py")
    assert is_test_file("src/foo_test.py")
    assert not is_test_file("app.py")
    assert not is_test_file("contest.py")
