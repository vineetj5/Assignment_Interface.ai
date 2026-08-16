import pytest
from automation.exceptions import ControlOwnershipError, SessionError
from automation.models import ControlOwner, SessionStatus
from automation.session import SessionManager


@pytest.mark.asyncio
async def test_session_lifecycle():
    manager = SessionManager(headless=True)
    assert manager.state.status == SessionStatus.ACTIVE
    assert manager.state.control_owner == ControlOwner.AUTOMATION

    # Start session
    page = await manager.start()
    assert page is not None
    assert manager.page is page

    # Pause and resume
    await manager.pause()
    assert manager.state.status == SessionStatus.PAUSED
    with pytest.raises(SessionError):
        manager.assert_action_permitted()

    await manager.resume()
    assert manager.state.status == SessionStatus.ACTIVE
    manager.assert_action_permitted()

    # Cede control to human
    await manager.cede_control()
    assert manager.state.control_owner == ControlOwner.HUMAN
    assert manager.state.status == SessionStatus.PAUSED
    with pytest.raises(ControlOwnershipError):
        manager.assert_action_permitted()

    await manager.reclaim_control()
    assert manager.state.control_owner == ControlOwner.AUTOMATION
    assert manager.state.status == SessionStatus.ACTIVE
    manager.assert_action_permitted()

    # Close session
    await manager.close()
    assert manager.state.status == SessionStatus.CLOSED
    with pytest.raises(SessionError):
        manager.assert_action_permitted()
