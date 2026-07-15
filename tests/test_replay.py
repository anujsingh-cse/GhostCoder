import os
import tempfile
import json
import pytest
from ghostcoder.replay import SafetyGuardrail, GhostReplay, GhostGuardrail

def test_ghost_guardrail_features():
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_file = os.path.join(tmpdir, "audit.log")
        guardrail = GhostGuardrail(audit_log_path=audit_file)
        
        # Test check_code_pattern database destructive
        violations = guardrail.check_code_pattern("DROP DATABASE users;")
        assert len(violations) == 1
        assert violations[0]["category"] == "database_destructive"
        assert violations[0]["severity"] == "critical"
        
        # Test check_code_pattern secret exposure
        secret_violations = guardrail.check_code_pattern("api_key = 'abcdefghijklmnopqrstuvwxyz123'")
        assert len(secret_violations) == 1
        assert secret_violations[0]["category"] == "secret_exposure"
        
        # Test check_action blocked
        decision = guardrail.check_action(
            agent_name="db-agent",
            action_type="sql_execution",
            original_code="",
            proposed_code="DROP DATABASE users;"
        )
        assert decision["allowed"] is False
        assert decision["severity"] == "critical"
        
        # Test check_file_operation blocked
        op_decision = guardrail.check_file_operation("/path/to/.git/config", "delete")
        assert op_decision["allowed"] is False
        assert op_decision["severity"] == "critical"
        
        # Test check_file_operation allowed
        op_allowed = guardrail.check_file_operation("/path/to/src/main.py", "modify")
        assert op_allowed["allowed"] is True
        
        # Verify audit log entries exist and are correct
        assert os.path.exists(audit_file)
        with open(audit_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) >= 3
        first_entry = json.loads(lines[0])
        assert first_entry["agent_name"] == "db-agent"
        assert first_entry["allowed"] is False

def test_safety_guardrail_harmless():
    suggestion = {
        "agent": "agency-senior-developer",
        "hint": "Check the loop index variable.",
        "fix": "for i in range(10):\n    print(i)"
    }
    checked = SafetyGuardrail.check_suggestion(suggestion)
    assert checked["blocked"] is False
    assert checked["fix"] is not None

def test_safety_guardrail_destructive():
    destructive_suggestion = {
        "agent": "agency-senior-developer",
        "hint": "Warning: Clean the build workspace.",
        "fix": "rm -rf /usr/bin"
    }
    checked = SafetyGuardrail.check_suggestion(destructive_suggestion)
    assert checked["blocked"] is True
    assert checked["fix"] is None
    assert "BLOCKED" in checked["hint"]
    
    ps_destructive = {
        "agent": "agency-senior-developer",
        "hint": "Remove temp dir recursively.",
        "fix": "Remove-Item -Path temp -Recurse"
    }
    checked_ps = SafetyGuardrail.check_suggestion(ps_destructive)
    assert checked_ps["blocked"] is True

def test_ghost_replay_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        replay = GhostReplay(sessions_dir=tmpdir)
        session_id = replay.start_session("mock_project", "mock_branch")
        
        assert session_id is not None
        assert replay.current_session_id == session_id
        
        # Log events
        replay.log_event("error_detected", {"error_message": "ReferenceError: x is not defined"})
        replay.log_event("agent_dispatched", {"agent": "agency-reality-checker"})
        replay.log_event("fix_suggested", {
            "agent": "agency-reality-checker",
            "hint": "Define x before using it",
            "fix": "x = 42",
            "file": "test.py"
        })
        replay.log_event("fix_applied", {
            "agent": "agency-reality-checker",
            "hint": "Define x before using it",
            "fix": "x = 42",
            "file": "test.py"
        })
        
        # Verify saved session
        session_data = replay.load_session(session_id)
        assert session_data["project"] == "mock_project"
        assert session_data["branch"] == "mock_branch"
        assert len(session_data["events"]) == 4
        
        # Verify explain_decision
        explanation = replay.explain_decision(session_id, 1)
        assert "# Explain Decision: Event #1" in explanation
        assert "agency-reality-checker" in explanation
        
        # Verify replay_session
        plan = replay.replay_session(session_id)
        assert len(plan) == 1
        assert plan[0]["fix"] == "x = 42"
        assert plan[0]["file"] == "test.py"
        
        # Verify generate_report
        report = replay.generate_report()
        assert report["sessions_analyzed"] == 1
        assert report["applied_fixes"] == 1
        assert report["estimated_time_saved_mins"] == 5
        assert report["agent_distribution"]["agency-reality-checker"] == 1
