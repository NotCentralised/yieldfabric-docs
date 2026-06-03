"""
Data-policy executor — register / approve / execute data-driven policies on
group ConfidentialAccounts (the `pipelineGate` GraphQL namespace), plus a
`whoami` helper that resolves the account addresses a policy needs.

The feature under test: a RESTRICTED group member (`policymember` role) runs a
group operation under a data policy via `executeUnderPolicy`. The relay→I→G
chain is: G = the group account (the policy account), I = the member's own
account (registered in the policy's `executors_address`). The group's owner is
the APPROVER (in `required_signers`) and signs the policy's reusable M-of-N
digest ONCE; the member EXECUTES but is deliberately absent from the caller set,
so it can never approve. Mirrors the contract's own restricted-member test
(yieldfabric-smart-contracts/test/ConfidentialAccountPolicy.test.ts).

Command types:

    whoami                → resolve & store account_address / group_account_address
                            / default_wallet_id / sub for a user (optionally acting
                            as a group), so the suite can thread addresses by name.
    add_data_policy       → pipelineGate.addDataPolicy   (MQ; register a policy on G)
    approve_data_policy   → pipelineGate.approveDataPolicy (record one reusable
                            approval signature, obtained from the auth REST sign API)
    execute_under_policy  → pipelineGate.executeUnderPolicy (MQ; run a bound op)
    data_policies         → pipelineGate.dataPolicies      (read, for asserts)
    data_policy_approval  → pipelineGate.dataPolicyApproval (read, for asserts)

Signing note: `approve_data_policy` never touches a private key. It fetches the
policy's registered digest, computes the EIP-191 message-hash for it
(`crypto.eip191_message_hash`, a library call — not a signature), asks the auth
REST API to sign that digest with the approver's server-custodied key
(`POST /key-operations/vault/sign`), and submits the returned signature.
"""

import json
from typing import Any, Dict, List, Optional

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.crypto import eip191_message_hash
from ..utils.graphql import DataPolicyGraphQL
from ..utils.jwt import decode_payload, get_sub
from ..utils.validators import is_provided


def _camel(snake: str) -> str:
    """`token_id` → `tokenId`. Idempotent for already-camelCase keys."""
    parts = str(snake).split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def _camel_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """camelCase the keys of a flat dict (values untouched)."""
    return {_camel(k): v for k, v in d.items()}


class PolicyExecutor(BaseExecutor):
    """Executor for data-driven policies on group accounts."""

    def execute(self, command: Command) -> CommandResponse:
        command_type = command.type.lower()
        dispatch = {
            "whoami": self._execute_whoami,
            "add_data_policy": self._execute_add_data_policy,
            "approve_data_policy": self._execute_approve_data_policy,
            "execute_under_policy": self._execute_execute_under_policy,
            "commit_oracle_document": self._execute_commit_oracle_document,
            "data_policies": self._execute_data_policies,
            "data_policy_approval": self._execute_data_policy_approval,
        }
        handler = dispatch.get(command_type)
        if handler is None:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown policy command type: {command_type}"],
            )
        return handler(command)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _claim(self, token: str, *names: str) -> Optional[str]:
        """First non-empty claim from the (unverified) JWT payload."""
        payload = decode_payload(token) or {}
        for n in names:
            v = payload.get(n)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    def _graphql(self, query: str, variables: dict, token: str):
        """Post a GraphQL operation (mutation or query) to payments /graphql."""
        return self.payments_service.graphql_mutation(query, variables, token)

    # ------------------------------------------------------------------
    # whoami — resolve the addresses a policy is wired from.
    # ------------------------------------------------------------------

    def _execute_whoami(self, command: Command) -> CommandResponse:
        """
        Log in (as the user, or acting as `user.group`) and surface the
        identity claims downstream policy commands need:

            <cmd>.account_address         the caller's own smart-account address
                                          (the unit registered as a policy
                                          approver/executor; = on-chain `I`)
            <cmd>.group_account_address   the acting group's account (= `G`,
                                          the policy account) — only when a
                                          group was requested
            <cmd>.default_wallet_id       the acting wallet id (the group's when
                                          delegating) — the `walletId` the policy
                                          off-chain projection lists under
            <cmd>.sub / <cmd>.user_id     the user UUID (the sign API `contact_id`)
        """
        self.log_command_start(command)
        # use_delegation honours user.group: with a group we get a delegation
        # JWT carrying group_account_address; without, a plain self token.
        token, err = self._acquire_token_or_error(
            command, use_delegation=bool(command.user.group)
        )
        if err:
            return err

        account_address = self._claim(token, "account_address")
        group_account_address = self._claim(token, "group_account_address")
        default_wallet_id = self._claim(token, "default_wallet_id")
        sub = get_sub(token)

        # Fallback: a deployed group's account address via account-status when
        # the delegation claim didn't carry it.
        if command.user.group and not group_account_address:
            group_id = self.auth_service.get_user_group_id_by_name(token, command.user.group)
            if group_id:
                info = self.auth_service.group_account_info(token, group_id)
                group_account_address = info.get("account_address") or None
                default_wallet_id = default_wallet_id or info.get("wallet_id")

        outputs = {
            "account_address": account_address,
            "group_account_address": group_account_address,
            "default_wallet_id": default_wallet_id,
            "sub": sub,
            "user_id": sub,
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"    ✅ whoami {command.user.id}"
            + (f" as {command.user.group}" if command.user.group else "")
            + f": account={account_address} group_account={group_account_address}"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    # ------------------------------------------------------------------
    # add_data_policy — register a policy on the group account (MQ).
    # ------------------------------------------------------------------

    def _execute_add_data_policy(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        # Registering a policy requires acting AS the group (require_group_policy_account).
        token, err = self._acquire_token_or_error(command, use_delegation=True)
        if err:
            return err

        p = command.parameters
        account_address = p.get("account_address") or self._claim(token, "group_account_address")
        wallet_id = p.get("wallet_id") or self._claim(token, "default_wallet_id")
        if not account_address:
            return self._fail(
                command,
                "add_data_policy requires `account_address` (the group account) — "
                "none provided and the JWT carries no group_account_address; submit while "
                "acting as the group (set user.group).",
            )

        policy_id = p.get("policy_id")
        if not policy_id:
            return self._fail(command, "add_data_policy requires `policy_id`")

        required_signers = p.get("required_signers") or []
        allowed_operations = p.get("allowed_operations") or []
        requirements = p.get("requirements") or []
        if not required_signers:
            return self._fail(command, "add_data_policy requires at least one `required_signers` entry")
        if not allowed_operations:
            return self._fail(command, "add_data_policy requires at least one `allowed_operations` entry")
        if not requirements:
            return self._fail(command, "add_data_policy requires at least one `requirements` entry")

        gql_input: Dict[str, Any] = {
            "accountAddress": account_address,
            "policyId": str(policy_id),
            "expiry": str(p.get("expiry", "0")),
            "maxUse": str(p.get("max_use", "1")),
            "minSignatories": int(p.get("min_signatories", 1)),
            "requiredSigners": list(required_signers),
            "allowedOperations": list(allowed_operations),
            "requirements": [_camel_keys(r) for r in requirements],
        }
        if wallet_id:
            gql_input["walletId"] = wallet_id
        for key, field in (
            ("start", "start"),
            ("policy_type", "policyType"),
        ):
            if is_provided(p.get(key)):
                gql_input[field] = str(p.get(key))
        if p.get("caller_ids"):
            gql_input["callerIds"] = [str(c) for c in p.get("caller_ids")]
        if p.get("executor_accounts"):
            gql_input["executorAccounts"] = list(p.get("executor_accounts"))
        if p.get("required_signer_entity_ids"):
            gql_input["requiredSignerEntityIds"] = list(p.get("required_signer_entity_ids"))
        if p.get("amount_bounds"):
            gql_input["amountBounds"] = [_camel_keys(b) for b in p.get("amount_bounds")]

        self.log_parameters({
            "account_address": account_address,
            "policy_id": policy_id,
            "min_signatories": gql_input["minSignatories"],
            "required_signers": required_signers,
            "executor_accounts": p.get("executor_accounts"),
            "allowed_operations": allowed_operations,
            "max_use": gql_input["maxUse"],
            "expiry": gql_input["expiry"],
        })

        response = self._graphql(DataPolicyGraphQL.ADD_DATA_POLICY, {"input": gql_input}, token)
        if not response.success:
            return self._finalize_graphql_error(command, response, operation_name="AddDataPolicy")

        data = response.get_data("pipelineGate.addDataPolicy", {}) or {}
        if not data.get("success"):
            return self._finalize_business_error(
                command, data.get("message", "addDataPolicy not successful"),
                operation_name="AddDataPolicy",
            )

        outputs = {
            "policy_id": data.get("policyId") or str(policy_id),
            "account_address": account_address,
            "message": data.get("message"),
            "message_id": data.get("messageId"),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"Data policy {outputs['policy_id']} registration submitted",
        )

    # ------------------------------------------------------------------
    # approve_data_policy — record one reusable M-of-N approval signature.
    # The signature comes from the auth REST sign API (no local key).
    # ------------------------------------------------------------------

    def _execute_approve_data_policy(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        # Approve AS the approver themselves: the off-chain eligibility gate matches
        # the approver's own account_address against the policy's caller set, and the
        # signature must recover to one of the approver's own owner EOAs.
        token, err = self._acquire_token_or_error(command, use_delegation=False)
        if err:
            return err

        p = command.parameters
        account_address = p.get("account_address")
        policy_id = p.get("policy_id")
        if not account_address or not policy_id:
            return self._fail(command, "approve_data_policy requires `account_address` and `policy_id`")

        # 1. Fetch the operation-independent digest the approver must sign.
        approval = self._graphql(
            DataPolicyGraphQL.DATA_POLICY_APPROVAL,
            {"accountAddress": account_address, "policyId": str(policy_id)},
            token,
        )
        if not approval.success:
            return self._finalize_graphql_error(command, approval, operation_name="GetDataPolicyApproval")
        info = approval.get_data("pipelineGate.dataPolicyApproval", {}) or {}
        registered_digest = info.get("registeredDigest")
        if not registered_digest:
            return self._fail(command, "approve_data_policy: could not resolve the policy's registered digest")

        # 2. Ask the auth REST API to sign the EIP-191 message-hash of the digest
        #    with the approver's server-custodied key. `contact_id` = the approver.
        contact_id = p.get("signer_contact_id") or get_sub(token)
        if not contact_id:
            return self._fail(command, "approve_data_policy: could not resolve the approver's id for signing")
        try:
            eip191_hash = eip191_message_hash(registered_digest)
        except Exception as e:  # pragma: no cover — bad digest is a backend bug
            return self._fail(command, f"approve_data_policy: failed to prepare digest: {e}")

        self.log_parameters({
            "account_address": account_address,
            "policy_id": policy_id,
            "registered_digest": registered_digest,
            "signer_contact_id": contact_id,
        })

        sign = self.auth_service.sign_vault(token, contact_id=contact_id, data=eip191_hash, data_format="hex")
        signature = sign.get("result") if isinstance(sign, dict) else None
        if not signature:
            return self._fail(
                command,
                f"approve_data_policy: vault/sign returned no signature ({sign.get('message') or sign})",
            )

        # 3. Submit the signature; the backend recovers the signer and tallies the M-of-N.
        response = self._graphql(
            DataPolicyGraphQL.APPROVE_DATA_POLICY,
            {"input": {"accountAddress": account_address, "policyId": str(policy_id), "signature": signature}},
            token,
        )
        if not response.success:
            return self._finalize_graphql_error(command, response, operation_name="ApproveDataPolicy")
        data = response.get_data("pipelineGate.approveDataPolicy", {}) or {}
        if not data.get("success"):
            return self._finalize_business_error(
                command, data.get("message", "approveDataPolicy not successful"),
                operation_name="ApproveDataPolicy",
            )

        outputs = {
            "account_address": account_address,
            "policy_id": str(policy_id),
            "signer": data.get("signer"),
            "collected": data.get("collected"),
            "approved": data.get("approved"),
            "message": data.get("message"),
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"    ✅ approve_data_policy {policy_id}: "
            f"collected={outputs['collected']} approved={outputs['approved']} signer={outputs['signer']}"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    # ------------------------------------------------------------------
    # execute_under_policy — run a bound op under the approved policy (MQ).
    # ------------------------------------------------------------------

    def _execute_execute_under_policy(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        # Executing requires acting AS the group (require_group_policy_account); the
        # PolicyMember's delegation is force-scoped to [PolicyExecution, CryptoOperations].
        token, err = self._acquire_token_or_error(command, use_delegation=True)
        if err:
            return err

        p = command.parameters
        account_address = p.get("account_address") or self._claim(token, "group_account_address")
        policy_id = p.get("policy_id")
        operation_type = p.get("operation_type")
        operation_data = p.get("operation_data")
        if not account_address:
            return self._fail(
                command,
                "execute_under_policy requires `account_address` (the group account) — "
                "submit while acting as the group (set user.group).",
            )
        if not policy_id or not operation_type:
            return self._fail(command, "execute_under_policy requires `policy_id` and `operation_type`")
        if not isinstance(operation_data, dict):
            return self._fail(command, "execute_under_policy requires `operation_data` (a mapping)")

        self.log_parameters({
            "account_address": account_address,
            "policy_id": policy_id,
            "operation_type": operation_type,
            "operation_data": operation_data,
        })

        gql_input = {
            "accountAddress": account_address,
            "policyId": str(policy_id),
            "operationType": str(operation_type),
            # The backend takes operationData as a JSON string (the inner op's Data shape).
            "operationData": json.dumps(operation_data),
        }
        response = self._graphql(DataPolicyGraphQL.EXECUTE_UNDER_POLICY, {"input": gql_input}, token)
        if not response.success:
            return self._finalize_graphql_error(command, response, operation_name="ExecuteUnderPolicy")
        data = response.get_data("pipelineGate.executeUnderPolicy", {}) or {}
        if not data.get("success"):
            return self._finalize_business_error(
                command, data.get("message", "executeUnderPolicy not successful"),
                operation_name="ExecuteUnderPolicy",
            )

        outputs = {
            "account_address": account_address,
            "policy_id": str(policy_id),
            "operation_type": str(operation_type),
            "collected": data.get("collected"),
            "approved": data.get("approved"),
            "message": data.get("message"),
            "message_id": data.get("messageId"),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"executeUnderPolicy {policy_id} ({operation_type}) submitted",
        )

    # ------------------------------------------------------------------
    # commit_oracle_document — publish a confidential document to the oracle
    # (MQ). The committing account becomes the `obligor` an oracle data
    # requirement names; `getCommitment(obligor, key)` reads it on-chain.
    # ------------------------------------------------------------------

    def _execute_commit_oracle_document(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command, use_delegation=bool(command.user.group))
        if err:
            return err

        p = command.parameters
        account_address = p.get("account_address") or self._claim(token, "group_account_address")
        key = p.get("key")
        value = p.get("value")
        document_json = p.get("document_json")
        if not account_address:
            return self._fail(command, "commit_oracle_document requires `account_address` (the committing account)")
        if not key or value is None or document_json is None:
            return self._fail(command, "commit_oracle_document requires `key`, `value`, and `document_json`")
        # document_json may be authored as a YAML mapping or a JSON string; normalise to a string.
        if isinstance(document_json, (dict, list)):
            document_json = json.dumps(document_json)

        gql_input = {
            "accountAddress": account_address,
            "key": str(key),
            "value": str(value),
            "documentJson": str(document_json),
        }
        if is_provided(p.get("oracle_address")):
            gql_input["oracleAddress"] = p.get("oracle_address")

        self.log_parameters({
            "account_address": account_address,
            "key": key,
            "value": value,
            "document_json": document_json,
        })

        response = self._graphql(DataPolicyGraphQL.COMMIT_ORACLE_DOCUMENT, {"input": gql_input}, token)
        if not response.success:
            return self._finalize_graphql_error(command, response, operation_name="CommitOracleDocument")
        data = response.get_data("pipelineGate.commitOracleDocument", {}) or {}
        if not data.get("success"):
            return self._finalize_business_error(
                command, data.get("message", "commitOracleDocument not successful"),
                operation_name="CommitOracleDocument",
            )

        outputs = {
            "account_address": account_address,
            "oracle_address": data.get("oracleAddress"),
            "key": data.get("key") or str(key),
            "message": data.get("message"),
            "message_id": data.get("messageId"),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"oracle document committed for key {outputs['key']}",
        )

    # ------------------------------------------------------------------
    # Read helpers (for asserts).
    # ------------------------------------------------------------------

    def _execute_data_policies(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command, use_delegation=bool(command.user.group))
        if err:
            return err
        wallet_id = command.parameters.get("wallet_id") or self._claim(token, "default_wallet_id")
        if not wallet_id:
            return self._fail(command, "data_policies requires `wallet_id` (or a group delegation token)")
        response = self._graphql(DataPolicyGraphQL.DATA_POLICIES, {"walletId": wallet_id}, token)
        if not response.success:
            return self._finalize_graphql_error(command, response, operation_name="DataPolicies")
        policies = response.get_data("pipelineGate.dataPolicies", []) or []
        outputs = {"wallet_id": wallet_id, "policies": policies, "policy_count": len(policies)}
        self.store_outputs(command.name, outputs)
        self.logger.success(f"    ✅ data_policies: {len(policies)} policy(ies)")
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    def _execute_data_policy_approval(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command, use_delegation=bool(command.user.group))
        if err:
            return err
        p = command.parameters
        account_address = p.get("account_address") or self._claim(token, "group_account_address")
        policy_id = p.get("policy_id")
        if not account_address or not policy_id:
            return self._fail(command, "data_policy_approval requires `account_address` and `policy_id`")
        response = self._graphql(
            DataPolicyGraphQL.DATA_POLICY_APPROVAL,
            {"accountAddress": account_address, "policyId": str(policy_id)},
            token,
        )
        if not response.success:
            return self._finalize_graphql_error(command, response, operation_name="DataPolicyApproval")
        info = response.get_data("pipelineGate.dataPolicyApproval", {}) or {}
        outputs = {
            "account_address": account_address,
            "policy_id": str(policy_id),
            "registered_digest": info.get("registeredDigest"),
            "min_signatories": info.get("minSignatories"),
            "collected": info.get("collected"),
            "approved": info.get("approved"),
        }
        self.store_outputs(command.name, outputs)
        self.logger.success(
            f"    ✅ data_policy_approval {policy_id}: "
            f"collected={outputs['collected']} approved={outputs['approved']}"
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

    # ------------------------------------------------------------------

    def _fail(self, command: Command, message: str) -> CommandResponse:
        self.log_command_failure(command)
        return CommandResponse.error_response(command.name, command.type, [message])
