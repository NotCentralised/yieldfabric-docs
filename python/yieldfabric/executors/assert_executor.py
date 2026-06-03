"""
Assertion executor — value assertions on prior-step outputs (Tier-1 outcome checks).

Unlike `expect_failure` (which only asserts a command failed), `assert` checks a CONCRETE
value — typically a `$<command_name>.<field>` reference resolved by the output store before
dispatch — against an expected value using exactly one comparison operator. Use it after a
query (`balance` / `obligations`) to verify the OUTCOME of an operation (whose balance moved,
how many obligations), not merely that the message executed. Nearly every swap bug found while
hardening this system was a "wrong party still settles" bug that a status-only check misses.

Reference syntax is `$<command_name>.<field>` (NO `$step.` prefix) — the same `$cmd.field`
the output store resolves elsewhere; the operator value may itself be a `$`-ref. NOTE: the
`obligations` query keys rows by on-chain `token_id`/`owner`, not the suite `contract_id`, so
do NOT `contains:`-assert a suite id against it — prefer a `balance` value or `count`.

YAML shape (exactly one operator):
    - name: assert_forfeit_credited_counterparty
      type: assert
      parameters:
        actual: "$bal_after.private_balance"    # substituted before we run
        gt: "$bal_before.private_balance"       # value may be a $-ref too

Operators: equals | not_equals | contains | not_contains | gte | gt | lte | lt
(`gte/gt/lte/lt` parse both sides as integers — confidential amounts are big-int strings.)

Optional `minus:` modifier — before comparing, `actual` becomes `(actual - minus)` as a
big-int. This makes EXACT balance-change / value-conservation checks first-class: snapshot a
balance before and after, then assert the delta is exactly the payment amount, e.g.

    - name: assert_upfront_credited_exactly
      type: assert
      parameters:
        actual: "$aud_after.private_balance"
        minus:  "$aud_before.private_balance"      # actual := after - before
        equals: "1000000000000000000000"           # delta must equal 1000 AUD exactly
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse


def _to_num(v):
    # Confidential amounts are arbitrary-precision integers serialized as strings; Python int
    # handles any size. Fall back to float for the rare decimal value.
    s = str(v).strip()
    try:
        return int(s)
    except ValueError:
        return float(s)


class AssertExecutor(BaseExecutor):
    """Executor for `assert` — compare a (already-substituted) value against an expected one."""

    _OPS = ("equals", "not_equals", "contains", "not_contains", "gte", "gt", "lte", "lt")

    def execute(self, command: Command) -> CommandResponse:
        p = command.parameters

        if p.get("actual") is None:
            return CommandResponse.error_response(
                command.name, command.type,
                ["assert: 'actual' is missing or an unresolved $step reference"],
            )
        actual = str(p.get("actual"))

        # Optional delta mode: actual := actual - minus (exact balance-change / conservation checks).
        if p.get("minus") is not None:
            try:
                actual = str(_to_num(actual) - _to_num(str(p.get("minus"))))
            except (TypeError, ValueError) as e:
                return CommandResponse.error_response(
                    command.name, command.type, [f"assert: non-numeric 'minus' ({e})"],
                )

        chosen = [op for op in self._OPS if p.get(op) is not None]
        if len(chosen) != 1:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"assert: provide exactly one of {self._OPS} (got {chosen or 'none'})"],
            )
        op = chosen[0]
        expected = str(p.get(op))

        try:
            if op == "equals":
                ok, desc = actual == expected, f"{actual!r} == {expected!r}"
            elif op == "not_equals":
                ok, desc = actual != expected, f"{actual!r} != {expected!r}"
            elif op == "contains":
                ok, desc = expected in actual, f"{expected!r} in {actual!r}"
            elif op == "not_contains":
                ok, desc = expected not in actual, f"{expected!r} NOT in {actual!r}"
            elif op == "gte":
                ok, desc = _to_num(actual) >= _to_num(expected), f"{actual} >= {expected}"
            elif op == "gt":
                ok, desc = _to_num(actual) > _to_num(expected), f"{actual} > {expected}"
            elif op == "lte":
                ok, desc = _to_num(actual) <= _to_num(expected), f"{actual} <= {expected}"
            else:  # lt
                ok, desc = _to_num(actual) < _to_num(expected), f"{actual} < {expected}"
        except (TypeError, ValueError) as e:
            return CommandResponse.error_response(
                command.name, command.type, [f"assert: non-numeric comparison ({e})"]
            )

        if ok:
            self.logger.success(f"🔎 {command.name}: assert passed ({desc})")
            return CommandResponse.success_response(
                command.name, command.type,
                {"assert": "passed", "check": desc},
                message=f"assert passed: {desc}",
            )
        self.logger.error(f"🔎 {command.name}: assert FAILED ({desc})")
        return CommandResponse.error_response(
            command.name, command.type, [f"assert FAILED: {desc}"]
        )
