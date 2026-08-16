"""Tests for Phase 6 chat session state."""

from routing.session import ChatSessionStore


def test_session_store_pending_state_lifecycle():
    store = ChatSessionStore()
    state = store.get("abc")
    state.pending_capability = "lookup_balance"
    state.collected_arguments = {"member_id": "12345"}
    state.missing_arguments = ["account_type"]
    store.save(state)

    loaded = store.get("abc")
    assert loaded.pending_capability == "lookup_balance"
    assert loaded.collected_arguments["member_id"] == "12345"

    cleared = store.clear_pending("abc")
    assert cleared.pending_capability is None
    assert cleared.collected_arguments == {}
    assert cleared.missing_arguments == []

