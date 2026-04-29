from src.core.communication.event_bus import GlobalEventBus


def _fresh_bus() -> GlobalEventBus:
    bus = GlobalEventBus.instance()
    bus.clear_history()
    return bus


def test_notification_history_tracks_direct_signal_emits():
    bus = _fresh_bus()

    bus.notification.emit("info", "Primeira", "Mensagem 1")
    bus.notification.emit("warning", "Segunda", "Mensagem 2")

    recent = bus.get_recent_notifications()

    assert len(recent) == 2
    assert recent[0]["type"] == "warning"
    assert recent[0]["title"] == "Segunda"
    assert recent[0]["message"] == "Mensagem 2"
    assert recent[1]["title"] == "Primeira"


def test_clear_history_clears_notification_history_too():
    bus = _fresh_bus()

    bus.notification.emit("success", "Tudo certo", "Concluído")
    assert bus.get_recent_notifications()

    bus.clear_history()

    assert bus.get_recent_notifications() == []
