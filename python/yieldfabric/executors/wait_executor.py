"""
Wait-executor — declarative `wait_for_*` command types for YAML flows.

Loan-management-style workflows sequence mutations with state-based
waits in between:

    - deposit               → wait_for_message
    - issue_workflow        → wait_for_workflow
    - completeSwap          → wait_for_swap
    - background listener   → wait_for_signatures_cleared
    - accept                → wait_for_accept_all  (accept + poll)

Rather than forcing callers to write Python, these are declarative
YAML commands backed by the polling helpers on PaymentsService.

Example YAML:

    - name: wait_issue
      type: wait_for_workflow
      user: { id: issuer@yieldfabric.com, password: issuer_password }
      parameters:
        workflow_id: $issue_workflow_1.workflow_id
        interval: 1.0       # optional, default 1.0
        timeout: 120        # optional, default 120

    - name: wait_swap
      type: wait_for_swap
      user: { id: ..., password: ... }
      parameters:
        swap_id: $create_swap_1.swap_id
        timeout: 120

    - name: wait_msg
      type: wait_for_message
      user: { id: ..., password: ... }
      parameters:
        message_id: $deposit_1.message_id
        user_id: $deposit_1.account_address       # (or JWT sub)

Every wait populates downstream-usable outputs on success:
    <name>.attempts, <name>.elapsed, <name>.observation (raw probe result)
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.jwt import get_sub


class WaitExecutor(BaseExecutor):
    """Executor for the wait_for_* declarative poll commands."""

    def execute(self, command: Command) -> CommandResponse:
        command_type = command.type.lower()

        if command_type == "wait_for_workflow":
            return self._wait_for_workflow(command)
        if command_type == "wait_for_swap":
            return self._wait_for_swap(command)
        if command_type == "wait_for_message":
            return self._wait_for_message(command)
        if command_type == "wait_for_signatures_cleared":
            return self._wait_for_signatures_cleared(command)
        if command_type == "wait_for_accept_all":
            return self._wait_for_accept_all(command)

        return CommandResponse.error_response(
            command.name, command.type,
            [f"Unknown wait command type: {command_type}"]
        )

    # ------------------------------------------------------------------

    def _get_interval(self, command: Command, default: float) -> float:
        raw = command.parameters.get("interval")
        try:
            return float(raw) if raw is not None else default
        except (TypeError, ValueError):
            return default

    def _get_timeout(self, command: Command, default: float) -> float:
        raw = command.parameters.get("timeout")
        try:
            return float(raw) if raw is not None else default
        except (TypeError, ValueError):
            return default

    # ------------------------------------------------------------------
    # wait_for_workflow
    # ------------------------------------------------------------------

    def _wait_for_workflow(self, command: Command) -> CommandResponse:
        self.log_command_start(command)

        workflow_id = command.parameters.get("workflow_id")
        if not workflow_id:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type,
                ["wait_for_workflow requires `workflow_id`"]
            )

        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        interval = self._get_interval(command, 1.0)
        timeout = self._get_timeout(command, 120.0)

        try:
            result = self.payments_service.poll_workflow_status(
                workflow_id, token, interval=interval, timeout=timeout
            )
        except TimeoutError as e:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [str(e)]
            )

        outputs = {
            "workflow_id": workflow_id,
            "workflow_status": (result.observation.get("workflow_status") or ""),
            "current_step": result.observation.get("current_step"),
            "workflow_type": result.observation.get("workflow_type"),
            "attempts": result.attempts,
            "elapsed": result.elapsed,
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"  ✅ workflow {workflow_id[:8]}... reached {outputs['workflow_status']} "
            f"in {result.attempts} attempt(s) / {result.elapsed:.1f}s"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    # ------------------------------------------------------------------
    # wait_for_swap
    # ------------------------------------------------------------------

    def _wait_for_swap(self, command: Command) -> CommandResponse:
        self.log_command_start(command)

        swap_id = command.parameters.swap_id or command.parameters.get("swap_id")
        if not swap_id:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["wait_for_swap requires `swap_id`"]
            )

        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        interval = self._get_interval(command, 2.0)
        timeout = self._get_timeout(command, 120.0)

        try:
            result = self.payments_service.poll_swap_completion(
                swap_id, token, interval=interval, timeout=timeout
            )
        except TimeoutError as e:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [str(e)]
            )

        outputs = {
            "swap_id": swap_id,
            "status": result.observation,
            "attempts": result.attempts,
            "elapsed": result.elapsed,
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"  ✅ swap {swap_id[:8]}... reached {result.observation} "
            f"in {result.attempts} attempt(s) / {result.elapsed:.1f}s"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    # ------------------------------------------------------------------
    # wait_for_message
    # ------------------------------------------------------------------

    def _wait_for_message(self, command: Command) -> CommandResponse:
        """
        Wait for `message_id` to have `executed` populated. Requires
        `message_id` and either explicit `user_id` (the subject of the
        message; defaults to the logged-in user's JWT sub if absent).
        """
        self.log_command_start(command)

        message_id = command.parameters.get("message_id")
        if not message_id:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["wait_for_message requires `message_id`"]
            )

        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        # The message lookup endpoint is keyed by user_id (the subject
        # of the MQ message, usually the acting user's id). If the YAML
        # doesn't provide it, derive it from the JWT `sub` claim.
        user_id = command.parameters.get("user_id") or get_sub(token)
        if not user_id:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type,
                ["wait_for_message could not determine user_id (JWT sub missing)"],
            )

        interval = self._get_interval(command, 2.0)
        timeout = self._get_timeout(command, 300.0)

        try:
            result = self.payments_service.poll_message_completion(
                user_id, message_id, token, interval=interval, timeout=timeout
            )
        except TimeoutError as e:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [str(e)]
            )

        outputs = {
            "message_id": message_id,
            "user_id": user_id,
            "executed": result.observation.get("executed"),
            "response": result.observation.get("response"),
            "attempts": result.attempts,
            "elapsed": result.elapsed,
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"  ✅ message {message_id[:8]}... executed "
            f"in {result.attempts} attempt(s) / {result.elapsed:.1f}s"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    # ------------------------------------------------------------------
    # wait_for_signatures_cleared
    # ------------------------------------------------------------------

    def _wait_for_signatures_cleared(self, command: Command) -> CommandResponse:
        self.log_command_start(command)

        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        user_id = command.parameters.get("user_id") or get_sub(token)
        if not user_id:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type,
                ["wait_for_signatures_cleared could not determine user_id"],
            )

        interval = self._get_interval(command, 2.0)
        timeout = self._get_timeout(command, 30.0)

        try:
            result = self.payments_service.poll_signatures_cleared(
                user_id, token, interval=interval, timeout=timeout
            )
        except TimeoutError as e:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [str(e)]
            )

        outputs = {
            "user_id": user_id,
            "remaining": result.observation,
            "attempts": result.attempts,
            "elapsed": result.elapsed,
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"  ✅ signature queue drained in "
            f"{result.attempts} attempt(s) / {result.elapsed:.1f}s"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    # ------------------------------------------------------------------
    # wait_for_accept_all — also SUBMITS the accept_all mutation.
    # ------------------------------------------------------------------

    def _wait_for_accept_all(self, command: Command) -> CommandResponse:
        """
        `accept_all` + poll until something is actually accepted. This
        is what payment workflows use after a completeSwap to absorb
        the payables the swap generated — see loan_management's
        payment_workflow.py for the canonical usage.

        Required: denomination, idempotency_key.
        Optional: obligor, walletId — filter targets when multiple
        pending payables exist.
        """
        self.log_command_start(command)

        params = command.parameters
        denomination = params.denomination or params.asset_id or params.get("denomination")
        idempotency_key = params.idempotency_key or params.get("idempotency_key")
        if not denomination or not idempotency_key:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type,
                ["wait_for_accept_all requires `denomination` and `idempotency_key`"]
            )

        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        interval = self._get_interval(command, 2.0)
        timeout = self._get_timeout(command, 90.0)

        try:
            result = self.payments_service.poll_accept_all_until_ready(
                token,
                denomination=denomination,
                idempotency_key=idempotency_key,
                obligor=params.obligor or params.get("obligor"),
                wallet_id=params.get("wallet_id"),
                interval=interval,
                timeout=timeout,
            )
        except TimeoutError as e:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [str(e)]
            )

        observation = result.observation
        outputs = {
            "denomination": denomination,
            "total_payments": observation.get("totalPayments"),
            "accepted_count": observation.get("acceptedCount"),
            "failed_count": observation.get("failedCount"),
            "message": observation.get("message"),
            "attempts": result.attempts,
            "elapsed": result.elapsed,
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"  ✅ accept_all {denomination}: accepted={outputs['accepted_count']} "
            f"failed={outputs['failed_count']} "
            f"in {result.attempts} attempt(s) / {result.elapsed:.1f}s"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)


