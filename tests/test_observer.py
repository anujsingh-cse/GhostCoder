import os
import tempfile
import shutil
from ghostcoder.observer import ProjectDetector, ErrorDetector

def test_project_detector():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock Node/React project
        with open(os.path.join(tmpdir, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"dependencies": {"react": "^18.0.0", "typescript": "^5.0.0"}}')
        
        stack = ProjectDetector.detect_stack(tmpdir)
        assert stack["type"] == "Node"
        assert "React" in stack["technologies"]
        assert "TypeScript" in stack["technologies"]
        assert stack["package_manager"] == "npm"

def test_error_detector_pytest():
    stdout = """
============================= FAILURES =============================
___________________________ test_failure ___________________________
    def test_failure():
>       assert 1 == 2
E       assert 1 == 2
tests/test_app.py:5: AssertionError
========================= 1 failed in 0.1s =========================
"""
    err = ErrorDetector.parse_error(stdout)
    assert err is not None
    assert err["type"] == "pytest/python"
    assert "AssertionError" in err["message"]

def test_error_detector_rust():
    stdout = """
error[E0308]: mismatched types
  --> src/main.rs:2:18
   |
 2 |     let x: u32 = "hello";
   |            ---   ^^^^^^^ expected `u32`, found `&str`
   |            |
   |            expected due to this
"""
    err = ErrorDetector.parse_error(stdout)
    assert err is not None
    assert err["type"] == "rustc"
    assert "mismatched types" in err["message"]

def test_error_detector_git():
    stdout = """
To github.com:user/repo.git
 ! [rejected]        main -> main (fetch first)
error: failed to push some refs to 'github.com:user/repo.git'
"""
    err = ErrorDetector.parse_error(stdout)
    assert err is not None
    assert err["type"] == "git"
    assert "rejected" in err["message"]
