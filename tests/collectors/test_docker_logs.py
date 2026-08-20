from homeport.collectors import docker_api


def _frame(stream: int, payload: bytes) -> bytes:
    return bytes([stream, 0, 0, 0]) + len(payload).to_bytes(4, "big") + payload


def test_demux_logs_concatenates_stdout_and_stderr_frames_in_order():
    raw = _frame(1, b"hello\n") + _frame(2, b"oops\n") + _frame(1, b"bye\n")

    assert docker_api._demux_logs(raw) == "hello\noops\nbye\n"


def test_demux_logs_returns_raw_text_when_stream_is_not_multiplexed():
    # Conteneur avec TTY : pas d'en-tête de 8 octets, du texte brut.
    raw = b"just plain tty output\nsecond line\n"

    assert docker_api._demux_logs(raw) == "just plain tty output\nsecond line\n"


def test_demux_logs_handles_empty_input():
    assert docker_api._demux_logs(b"") == ""


def test_demux_logs_falls_back_to_raw_on_a_truncated_frame():
    # En-tête annonçant 99 octets mais seulement 3 présents : on ne perd rien, on rend le brut.
    raw = bytes([1, 0, 0, 0]) + (99).to_bytes(4, "big") + b"abc"

    assert "abc" in docker_api._demux_logs(raw)
