"""Unit tests for yieldfabric.utils.polling."""

import time

import pytest

from yieldfabric.utils.polling import PollResult, poll_until


def test_poll_until_succeeds_on_first_attempt_when_predicate_true():
    res = poll_until(
        probe=lambda: "done",
        done=lambda obs: obs == "done",
        interval=0.01,
        timeout=1.0,
        description="any value",
    )
    assert isinstance(res, PollResult)
    assert res.observation == "done"
    assert res.attempts == 1
    assert res.elapsed < 0.5  # should return immediately, no sleep


def test_poll_until_iterates_until_predicate_true():
    counter = {"n": 0}

    def probe():
        counter["n"] += 1
        return counter["n"]

    res = poll_until(
        probe=probe,
        done=lambda n: n >= 3,
        interval=0.01,
        timeout=2.0,
        description="counter to reach 3",
    )
    assert res.observation == 3
    assert res.attempts == 3


def test_poll_until_raises_timeout_error_with_diagnostic():
    with pytest.raises(TimeoutError) as excinfo:
        poll_until(
            probe=lambda: "still waiting",
            done=lambda obs: False,
            interval=0.05,
            timeout=0.15,
            description="a condition that never fires",
        )
    msg = str(excinfo.value)
    assert "a condition that never fires" in msg
    assert "still waiting" in msg  # last observation echoed
    assert "attempt" in msg


def test_poll_until_rejects_zero_interval():
    with pytest.raises(ValueError, match="interval"):
        poll_until(
            probe=lambda: None,
            done=lambda _: True,
            interval=0,
            timeout=1,
            description="invalid",
        )


def test_poll_until_rejects_negative_timeout():
    with pytest.raises(ValueError, match="timeout"):
        poll_until(
            probe=lambda: None,
            done=lambda _: True,
            interval=0.1,
            timeout=-1,
            description="invalid",
        )


def test_poll_until_runs_probe_at_least_once_before_timeout():
    # With timeout=0 and predicate=False, we still run probe once
    # before raising — predicates shouldn't be skipped just because
    # the timeout is at-the-limit.
    probed = {"n": 0}

    def probe():
        probed["n"] += 1
        return False

    with pytest.raises(TimeoutError):
        poll_until(
            probe=probe,
            done=lambda _: False,
            interval=0.05,
            timeout=0.01,  # tiny timeout
            description="one probe guaranteed",
        )
    assert probed["n"] >= 1


def test_poll_until_calls_on_tick_each_iteration():
    ticks = []

    def on_tick(attempt, obs):
        ticks.append((attempt, obs))

    counter = {"n": 0}

    def probe():
        counter["n"] += 1
        return counter["n"]

    poll_until(
        probe=probe,
        done=lambda n: n >= 4,
        interval=0.01,
        timeout=2.0,
        description="count to 4",
        on_tick=on_tick,
    )
    assert ticks == [(1, 1), (2, 2), (3, 3), (4, 4)]


def test_poll_until_swallows_tick_exceptions():
    # A misbehaving on_tick must not derail the poll itself.
    def bad_tick(*_args):
        raise RuntimeError("tick blew up")

    res = poll_until(
        probe=lambda: 42,
        done=lambda obs: obs == 42,
        interval=0.01,
        timeout=1.0,
        description="anything",
        on_tick=bad_tick,
    )
    assert res.observation == 42
