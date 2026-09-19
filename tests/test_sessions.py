from langchain_core.messages import AIMessage, HumanMessage

from harness.chat.session import Session
from harness.chat.sessions import SavedSession, saved_sessions
from harness.chat.store import open_store
from harness.tui.pick import pick_session
from tests.conftest import FakeToolChatModel


def run_conversation(settings, store, tmp_path, text, reply):
    session = Session.start(
        settings,
        store,
        cwd=tmp_path,
        model=FakeToolChatModel(messages=iter([AIMessage(content=reply)])),
    )
    session.graph.invoke({"messages": [HumanMessage(content=text)]}, session.config)
    return session


def test_saved_sessions_empty(tmp_path):
    store = open_store(tmp_path / "sessions.db")
    assert saved_sessions(store, 10) == []


def test_saved_sessions_newest_first_and_limit(settings, tmp_path):
    store = open_store(tmp_path / "sessions.db")
    run_conversation(settings, store, tmp_path, "first hi", "r1")
    run_conversation(settings, store, tmp_path, "second yo", "r2")
    saved = saved_sessions(store, 10)
    assert len(saved) == 2
    assert saved[0].first_message == "second yo"
    assert saved[1].first_message == "first hi"
    assert saved_sessions(store, 1) == saved[:1]


def test_conversation_survives_reopen(settings, tmp_path):
    path = tmp_path / "sessions.db"
    first = open_store(path)
    session = run_conversation(settings, first, tmp_path, "remember me", "ok")
    session_id = session.session_id
    second = open_store(path)
    saved = saved_sessions(second, 10)
    assert [item.session_id for item in saved] == [session_id]
    resumed = Session.resume(
        settings,
        session_id,
        second,
        cwd=tmp_path,
        model=FakeToolChatModel(messages=iter([AIMessage(content="again")])),
    )
    state = resumed.graph.get_state(resumed.config)
    texts = [m.content for m in state.values["messages"] if isinstance(m, HumanMessage)]
    assert "remember me" in texts


def test_pick_session():
    sessions = [
        SavedSession(session_id="a", started="t1", first_message="one"),
        SavedSession(session_id="b", started="t2", first_message="two"),
    ]
    assert pick_session(sessions, "1") == sessions[0]
    assert pick_session(sessions, "2") == sessions[1]
    assert pick_session(sessions, "") is None
    assert pick_session(sessions, "x") is None
    assert pick_session(sessions, "0") is None
    assert pick_session(sessions, "3") is None
