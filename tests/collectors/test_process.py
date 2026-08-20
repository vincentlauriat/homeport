import asyncio
import time

from homeport.collectors import _process


def test_run_returns_stdout_on_success():
    out = asyncio.run(_process.run("echo", "hello", timeout=5.0))
    assert out == b"hello\n"


def test_run_returns_none_for_a_missing_binary():
    out = asyncio.run(_process.run("this-binary-does-not-exist-xyz", timeout=5.0))
    assert out is None


def test_run_kills_the_child_on_timeout_instead_of_waiting_for_it():
    start = time.monotonic()

    out = asyncio.run(_process.run("sleep", "5", timeout=0.2))
    elapsed = time.monotonic() - start

    assert out is None
    assert elapsed < 2.0
