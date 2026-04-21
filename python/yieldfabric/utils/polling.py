"""
Generic event-based polling utility.

Every "wait for something to happen" in the YieldFabric workflow stack
is a predicate-over-real-state loop, NOT a fixed `time.sleep(N)` timer.
The caller supplies:

  - A `probe` callable that queries real state (HTTP GET, GraphQL query,
    etc.) and returns the current observation.
  - A `done` predicate that inspects the observation and decides whether
    we've arrived (terminal state, count > 0, field present, etc.).

`poll_until` loops: probe → done? → yes: return the observation;
no: sleep `interval`, retry until `timeout` elapses. Raises TimeoutError
with a user-facing reason on timeout so callers can recover / bail.

This is the foundational primitive for every `poll_*` / `wait_for_*`
method elsewhere in the framework. Do not add blind sleeps as a
substitute — write a new probe/done pair instead.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class PollResult(Generic[T]):
    """
    Result of a successful `poll_until` run.

    `observation` is whatever the probe returned on the final iteration.
    `attempts` is the number of probe calls made (1-indexed — always >= 1).
    `elapsed` is the wall-clock seconds from the first probe to the
    successful one.
    """

    observation: T
    attempts: int
    elapsed: float


def poll_until(
    probe: Callable[[], T],
    done: Callable[[T], bool],
    *,
    interval: float = 2.0,
    timeout: float = 120.0,
    description: str = "condition",
    on_tick: Optional[Callable[[int, T], None]] = None,
) -> PollResult[T]:
    """
    Repeatedly call `probe`, return the observation when `done(obs)` is
    True. Raise TimeoutError when `timeout` elapses without success.

    Args:
        probe: zero-argument callable that queries current state. Called
            at least once before `done` is checked.
        done: predicate — returns True iff the probe result indicates
            we can stop polling successfully.
        interval: seconds between probes. Default 2.0s.
        timeout: total seconds to wait before giving up. Default 120s.
        description: human-readable phrase for the thing being waited
            on. Surfaces in the TimeoutError message, e.g. "workflow
            status completed". Pick a phrase that finishes the sentence
            "timed out waiting for {description}".
        on_tick: optional callback invoked on every iteration with
            `(attempt_number, observation)`. Useful for progress logging
            without polluting the poll helper itself.

    Returns:
        PollResult — observation, attempt count, elapsed seconds.

    Raises:
        TimeoutError: when `timeout` seconds elapsed without `done`
            becoming True. Message includes description + attempts +
            elapsed time for diagnosis.

    Example:
        >>> res = poll_until(
        ...     probe=lambda: http.get("/status").json(),
        ...     done=lambda o: o["status"] in ("completed", "failed"),
        ...     interval=1.0,
        ...     timeout=60.0,
        ...     description="workflow to reach a terminal state",
        ... )
        >>> print(res.observation["status"], "after", res.attempts, "tries")

    The function intentionally takes NO shortcuts: the first probe is
    NOT elided even if `timeout == 0`, because callers should get one
    honest check before any timeout fires.
    """
    if interval <= 0:
        raise ValueError("interval must be > 0 (no blind tight loops)")
    if timeout < 0:
        raise ValueError("timeout must be >= 0")

    start = time.monotonic()
    attempts = 0
    last_observation: Optional[T] = None

    while True:
        attempts += 1
        observation = probe()
        last_observation = observation
        if on_tick is not None:
            try:
                on_tick(attempts, observation)
            except Exception:
                # Callback failure must not derail the poll. Log nothing
                # here — it's up to the caller to handle their own tick
                # exceptions. Silent swallow is acceptable only because
                # tick is advisory.
                pass

        if done(observation):
            return PollResult(
                observation=observation,
                attempts=attempts,
                elapsed=time.monotonic() - start,
            )

        elapsed = time.monotonic() - start
        remaining = timeout - elapsed
        if remaining <= 0:
            raise TimeoutError(
                f"timed out waiting for {description} after "
                f"{attempts} attempt(s) / {elapsed:.1f}s "
                f"(last observation: {_short_repr(last_observation)})"
            )

        # Sleep either the full interval or the remaining time, whichever
        # is smaller — this makes the final attempt happen right at the
        # deadline rather than overshooting.
        time.sleep(min(interval, remaining))


def _short_repr(value, max_len: int = 160) -> str:
    """Shorten repr for error messages; avoid dumping huge payloads."""
    try:
        s = repr(value)
    except Exception:
        s = "<unreprable>"
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s
