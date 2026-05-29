"""
Base executor class
"""

from typing import Callable, Optional, Tuple, Union

from ..config import YieldFabricConfig
from ..models import Command, CommandResponse
from ..services import AuthService, PaymentsService
from ..models.response import GraphQLResponse
from ..core.output_store import OutputStore
from ..utils.jwt import get_entity_id
from ..utils.logger import get_logger
from ..utils.validators import is_provided


class BaseExecutor:
    """Base class for command executors."""
    
    def __init__(self, auth_service: AuthService, payments_service: PaymentsService,
                 output_store: OutputStore, config: YieldFabricConfig,
                 token_manager=None):
        """
        Initialize executor.
        
        Args:
            auth_service: Auth service client
            payments_service: Payments service client
            output_store: Output store for variable substitution
            config: YieldFabric configuration
            token_manager: Optional shared token/session manager
        """
        self.auth_service = auth_service
        self.payments_service = payments_service
        self.output_store = output_store
        self.config = config
        self.token_manager = token_manager
        self.logger = get_logger(debug=config.debug)
    
    def execute(self, command: Command) -> CommandResponse:
        """
        Execute a command.
        
        Args:
            command: Command to execute
            
        Returns:
            CommandResponse object
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    def get_token(self, command: Command) -> Optional[str]:
        """
        Get JWT token for user (with optional group delegation).
        
        Args:
            command: Command containing user information
            
        Returns:
            JWT token or None if authentication fails
        """
        user = command.user

        if self.token_manager:
            return self.token_manager.get_token(
                user.id,
                user.password,
                group_name=user.group,
                use_delegation=True,
            )
        
        if user.group:
            # Login with group delegation
            return self.auth_service.login_with_group(user.id, user.password, user.group)
        else:
            # Regular login
            return self.auth_service.login(user.id, user.password)

    def _token_supplier(
        self,
        command: Command,
        *,
        use_delegation: bool = True,
    ) -> Callable[[], Optional[str]]:
        """Return a callable that refreshes the command token as needed."""
        if self.token_manager:
            return self.token_manager.token_supplier(
                command.user.id,
                command.user.password,
                group_name=command.user.group,
                use_delegation=use_delegation,
            )
        if use_delegation:
            return lambda: self.get_token(command)
        return lambda: self.auth_service.login(command.user.id, command.user.password)

    def _token_for_polling(
        self,
        command: Command,
        token: str,
        *,
        use_delegation: bool = True,
    ) -> Union[str, Callable[[], Optional[str]]]:
        """Use a refresh-aware supplier only when a manager is installed."""
        if self.token_manager:
            return self._token_supplier(command, use_delegation=use_delegation)
        return token
    
    def store_outputs(self, command_name: str, data: dict):
        """
        Store command outputs for variable substitution.
        
        Args:
            command_name: Name of the command
            data: Dictionary of field names and values to store
        """
        for field_name, value in data.items():
            if value is not None:
                self.output_store.store(command_name, field_name, value)
    
    def log_command_start(self, command: Command):
        """Log command start."""
        self.logger.command_start(command.name, command.type)
        self.logger.info(f"  User: {command.user.id}")
        if command.user.group:
            self.logger.cyan(f"  Group: {command.user.group} (delegation)")
    
    def log_command_success(self, command: Command):
        """Log command success."""
        self.logger.command_success(command.name)
    
    def log_command_failure(self, command: Command):
        """Log command failure."""
        self.logger.command_failure(command.name)
    
    def log_parameters(self, params: dict):
        """Log command parameters."""
        self.logger.info("  Parameters after substitution:")
        for key, value in params.items():
            if is_provided(value):
                self.logger.parameter(key, str(value))

    # ------------------------------------------------------------------
    # Event-based polling baked into every async command.
    #
    # The pattern: every MQ-backed mutation returns `message_id`. By
    # default, we poll the message-status endpoint until `executed` is
    # populated before returning. That keeps YAML execution sequenced by
    # real backend state instead of the shell harness's blanket
    # `COMMAND_DELAY`. Callers can opt out with `parameters.wait: false`
    # for fire-and-forget workloads.
    #
    # Executors call `_maybe_wait_for_execution` after a successful
    # submission and BEFORE storing final outputs. Downstream commands
    # can then reference `$cmd.executed_at`, `$cmd.execution_response`,
    # etc.
    # ------------------------------------------------------------------

    _DEFAULT_WAIT_TIMEOUT_SEC = 300.0
    _DEFAULT_WAIT_INTERVAL_SEC = 2.0

    def _should_wait(self, command: Command) -> bool:
        """Wait by default; only an explicit falsey `wait` disables it."""
        value = command.parameters.get("wait")
        if value is None:
            return True
        if value is False:
            return False
        if isinstance(value, str):
            return value.strip().lower() not in ("false", "0", "no", "off")
        return bool(value)

    def _wait_was_explicit(self, command: Command) -> bool:
        return command.parameters.get("wait") is not None

    def _maybe_wait_for_execution(
        self,
        command: Command,
        token: str,
        message_id: Optional[str],
        outputs: dict,
    ) -> Optional[str]:
        """
        Unless `parameters.wait` is explicitly false, block until the MQ
        consumer has executed `message_id`. Merge polling metadata into
        `outputs` so downstream commands can reference it:

            <cmd>.executed_at         timestamp the message finished
            <cmd>.execution_response  full backend response (dict)
            <cmd>.wait_attempts       number of polls performed
            <cmd>.wait_elapsed        wall-clock seconds spent waiting
            <cmd>.wait_timed_out      True only when the poll exceeded
                                      the timeout (kept under the
                                      wait_timeout ceiling)

        `wait: false` is a no-op. A missing `message_id` is logged as a
        warning only when the YAML explicitly requested waiting — some
        commands are pure reads or synchronous REST calls and naturally
        produce no MQ message.
        """
        if not self._should_wait(command):
            return None
        if not message_id:
            if self._wait_was_explicit(command):
                self.logger.warning(
                    "  ⚠️  wait requested but the command did not return a "
                    "message_id; nothing to poll"
                )
            return None

        entity_id = command.parameters.get("user_id") or get_entity_id(token)
        if not entity_id:
            return (
                "wait requested but could not derive entity_id from JWT; "
                "cannot poll message completion"
            )

        timeout = self._float_param(command, "wait_timeout", self._DEFAULT_WAIT_TIMEOUT_SEC)
        interval = self._float_param(command, "wait_interval", self._DEFAULT_WAIT_INTERVAL_SEC)

        self.logger.info(
            f"  ⏳ polling message {message_id[:8]}... "
            f"(interval={interval}s, timeout={timeout}s)"
        )
        try:
            result = self.payments_service.poll_message_completion(
                entity_id,
                message_id,
                self._token_for_polling(command, token),
                interval=interval,
                timeout=timeout,
            )
        except TimeoutError as e:
            self.logger.error(f"  ❌ message polling timed out: {e}")
            outputs["wait_timed_out"] = True
            outputs["wait_error"] = str(e)
            return str(e)

        outputs["executed_at"] = result.observation.get("executed")
        outputs["execution_response"] = result.observation.get("response")
        if isinstance(result.observation.get("response"), dict):
            outputs["post_processed_at"] = result.observation["response"].get(
                "post_processed_at"
            )
        outputs["wait_attempts"] = result.attempts
        outputs["wait_elapsed"] = result.elapsed
        self.logger.success(
            f"    ✅ message {message_id[:8]}... processed in "
            f"{result.attempts} attempt(s) / {result.elapsed:.1f}s"
        )
        return self._message_execution_error(result.observation)

    def _message_execution_error(self, observation: dict) -> Optional[str]:
        """Return an error message when the final MQ response is failed."""
        response = observation.get("response")
        if not isinstance(response, dict):
            return None

        status = str(response.get("status") or "").lower()
        success = response.get("success")
        if success is False or status in {"failed", "error"}:
            return (
                response.get("error")
                or response.get("error_message")
                or response.get("message")
                or "message execution failed"
            )
        return None

    def _float_param(self, command: Command, name: str, default: float) -> float:
        raw = command.parameters.get(name)
        try:
            return float(raw) if raw is not None else default
        except (TypeError, ValueError):
            return default

    # ------------------------------------------------------------------
    # Executor flow helpers — reduce boilerplate in the ~17 mutation
    # executor methods without forcing a heavy template-method pattern.
    #
    # Each executor still owns the "build mutation + extract outputs"
    # middle. These helpers only collapse the boilerplate prefix
    # (log_start + acquire_token + bail-on-no-token) and suffix
    # (wait + store + log_success + return).
    # ------------------------------------------------------------------

    def _acquire_token_or_error(
        self,
        command: Command,
        *,
        use_delegation: bool = True,
    ) -> Tuple[Optional[str], Optional[CommandResponse]]:
        """
        Get a JWT, returning either `(token, None)` for the caller to
        proceed or `(None, error_response)` to short-circuit.

        `use_delegation=True` (default) honours `command.user.group`:
        if set, we request a delegation JWT scoped to that group.
        Group-admin operations want to pass `use_delegation=False`
        because they use `user.group` only as a group-lookup hint (to
        resolve group_id by name) and must operate as the DIRECT user,
        not as the group — otherwise the on-chain owner/member
        endpoints reject the call.

        Usage:
            self.log_command_start(command)
            token, err = self._acquire_token_or_error(command)
            if err:
                return err
        """
        if use_delegation:
            token = self.get_token(command)
        elif self.token_manager:
            token = self.token_manager.get_token(
                command.user.id,
                command.user.password,
                group_name=command.user.group,
                use_delegation=False,
            )
        else:
            token = self.auth_service.login(command.user.id, command.user.password)
        if token:
            return token, None
        self.log_command_failure(command)
        return None, CommandResponse.error_response(
            command.name, command.type, ["Failed to get JWT token"]
        )

    # Fields that are expected to be present on every success response
    # but are not worth echoing back to the user as per-field log lines
    # (they're either noisy or duplicated elsewhere in the output).
    _OUTPUT_LOG_SKIP_KEYS = frozenset({
        # Wait-related metadata already surfaced by _maybe_wait_for_execution.
        "executed_at", "post_processed_at", "execution_response",
        "wait_attempts", "wait_elapsed",
        "wait_timed_out", "wait_error",
    })

    def _finalize_success(
        self,
        command: Command,
        token: str,
        outputs: dict,
        *,
        success_message: str,
    ) -> CommandResponse:
        """
        Common tail for every successful async submission:

            1. Poll for execution unless `parameters.wait` is false.
            2. Store outputs for variable substitution.
            3. Log success + echo each non-None output field at info
               level so users running without DEBUG still see the
               useful bits (message_id, contract_id, swap_id, etc.).
            4. log_command_success.
            5. Wrap in CommandResponse.success_response.
        """
        wait_error = self._maybe_wait_for_execution(
            command, token, outputs.get("message_id"), outputs
        )
        self.store_outputs(command.name, outputs)
        if wait_error:
            self.logger.error(f"    ❌ Message execution failed: {wait_error}")
            self.log_command_failure(command)
            return CommandResponse(
                success=False,
                command_name=command.name,
                command_type=command.type,
                message="Command execution failed",
                data=outputs,
                errors=[wait_error],
            )
        self.logger.success(f"    ✅ {success_message}")
        for key, value in outputs.items():
            if key in self._OUTPUT_LOG_SKIP_KEYS:
                continue
            if value is None or value == "" or value == []:
                continue
            # Large nested payloads (execution_response etc.) are logged
            # structurally by stored_output in debug mode — avoid dumping
            # the raw dict into info.
            if isinstance(value, (dict, list)):
                self.logger.info(f"      {key}: <{type(value).__name__} len={len(value)}>")
            else:
                self.logger.info(f"      {key}: {value}")
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    def _finalize_graphql_error(
        self,
        command: Command,
        response: GraphQLResponse,
        *,
        operation_name: str,
    ) -> CommandResponse:
        """
        Common tail for a GraphQL-level failure (HTTP/transport error or
        `errors` array in the response). Falls back to a generic
        "{operation_name} failed" when the response has no specific
        message.
        """
        msg = response.get_error_message() or f"{operation_name} failed"
        self.logger.error(f"    ❌ {operation_name} failed: {msg}")
        self.log_command_failure(command)
        return CommandResponse.error_response(
            command.name, command.type, [msg]
        )

    def _finalize_business_error(
        self,
        command: Command,
        message: str,
        *,
        operation_name: str,
    ) -> CommandResponse:
        """
        Common tail for a BUSINESS-level failure — the HTTP/GraphQL
        round-trip succeeded but the mutation itself returned
        `success: false` with a reason. Distinct from
        `_finalize_graphql_error` because the transport was fine;
        the operation semantically failed.
        """
        self.logger.error(f"    ❌ {operation_name} failed: {message}")
        self.log_command_failure(command)
        return CommandResponse.error_response(
            command.name, command.type, [message]
        )
