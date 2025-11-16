# Annuity Custom Handlers

This guide documents the custom annuity endpoints implemented in `yieldfabric-payments/src/handlers/custom`, and shows how to exercise them using the example scripts under `yieldfabric-docs/annuities/`.

All endpoints are authenticated with JWT tokens issued by the Auth service. Each script below handles login, token extraction, and error reporting so you can focus on the flow.

## Endpoints Overview

| Endpoint | Method | Purpose | Example Script |
| --- | --- | --- | --- |
| `/api/annuity/issue` | `POST` | Orchestrates obligation creation, acceptance, and swap creation to issue a new annuity. | `issue_annuity.sh` |
| `/api/annuity/issue_workflow` | `POST` | Starts the asynchronous annuity issuance WorkFlow and returns a `workflow_id`. | `issue_workflow.sh` |
| `/api/annuity/issue_workflow/{workflow_id}` | `GET` | Polls the status/result of an ongoing annuity issuance WorkFlow. | `issue_workflow.sh`, `issue_polling.sh` |
| `/api/annuity/settle` | `POST` | Completes an annuity swap and optionally accepts resulting payments. | `settle_annuity.sh` |
| `/api/annuity/settle_workflow` | `POST` | Starts the asynchronous annuity settlement WorkFlow and returns a `workflow_id`. | `settle_workflow.sh` |
| `/api/annuity/settle_workflow/{workflow_id}` | `GET` | Polls the status/result of an ongoing annuity settlement WorkFlow. | `settle_workflow.sh` |
| `/api/annuity/{annuity_id}` | `GET` | Retrieves annuity (swap) details, including issuer info and aggregated payments with obligor metadata. | `get_annuity.sh` |
| `/api/annuities` | `GET` | Lists annuities linked to the caller (issuer or counterparty) with basic status metadata. | `list_annuities.sh` |

## API Schemas (Swagger Style)

### POST /api/annuity/issue

**Description**

Issues a new annuity by creating and accepting the issuer obligations and then creating the associated swap.

**Headers**
- `Authorization: Bearer <JWT>`

**Request Body**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `denomination` | string | ✔ | Currency code for all obligations and payments. |
| `counterpart` | string | ✔ | Email/identifier of the counterparty entity. |
| `start_date` | string (ISO-8601) | ✔ | Contract start. |
| `end_date` | string (ISO-8601) | ✔ | Contract maturity. |
| `coupon_amount` | string | ✔ | Amount for each coupon payment. |
| `coupon_dates` | array of ISO-8601 strings | ✔ | Payment schedule for coupons. |
| `initial_amount` | string | ✔ | Principal amount for the annuity obligation. |
| `redemption_amount` | string | ✔ | Redemption amount for the counterpart obligation. |

**Example Request**

```json
{
  "denomination": "aud-token-asset",
  "counterpart": "collateral@yieldfabric.com",
  "start_date": "2025-12-01T00:00:00Z",
  "end_date": "2025-12-10T23:59:59Z",
  "coupon_amount": "5",
  "coupon_dates": [
    "2025-12-01T00:00:00Z",
    "2025-12-02T00:00:00Z",
    "2025-12-03T00:00:00Z"
  ],
  "initial_amount": "100",
  "redemption_amount": "100"
}
```

**Success Response (200)**

```json
{
  "status": "success",
  "timestamp": "2025-12-01T00:00:00Z",
  "result": {
    "annuity_contract_id": "string",
    "annuity_message_id": "string",
    "annuity_accept_message_id": "string",
    "redemption_contract_id": "string",
    "redemption_message_id": "string",
    "redemption_accept_message_id": "string",
    "annuity_id": "string",
    "swap_message_id": "string"
  },
  "error": null
}
```

**Error Response**

```json
{
  "status": "error",
  "timestamp": "...",
  "result": null,
  "error": "description"
}
```

---

### POST /api/annuity/settle

**Description**

Completes an existing annuity swap and optionally accepts resulting payments for the counterparty.

**Headers**
- `Authorization: Bearer <JWT>`

**Request Body**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `annuity_id` | string | ✔ | Identifier returned by the issuance flow. |
| `accept_payments` | boolean | ✖ | Set to `true` to run the accept-all mutation after completion. |

**Example Request**

```json
{
  "annuity_id": "1762474228883",
  "accept_payments": true
}
```

**Success Response (200)**

```json
{
  "status": "success",
  "timestamp": "2025-12-01T00:00:00Z",
  "result": {
    "annuity_id": "string",
    "complete_swap_message_id": "string",
    "counterparty_accept_message_id": "string|null",
    "issuer_accept_message_id": "string|null"
  },
  "error": null
}
```

**Error Response**

```json
{
  "status": "error",
  "timestamp": "...",
  "result": null,
  "error": "description"
}
```

---

### GET /api/annuity/{annuity_id}

**Description**

Returns the full annuity (swap) detail, including issuer metadata and aggregated payment information.

**Headers**
- `Authorization: Bearer <JWT>`

**Path Parameters**
- `annuity_id` (string) — Identifier returned by the issuance flow.

**Success Response (200)**

```json
{
  "status": "success",
  "timestamp": "2025-12-01T00:00:00Z",
  "result": {
    "annuity_id": "string",
    "status": "PENDING|ACTIVE|COMPLETED|CANCELLED|EXPIRED",
    "deadline": "ISO-8601",
    "issuer": {
      "id": "string",
      "email": "string|null"
    },
    "payments": [
      {
        "id": "string",
        "contract_id": "string",
        "amount": 100,
        "status": "string",
        "due_date": "ISO-8601|null",
        "obligor": {
          "wallet": {
            "id": "string",
            "address": "string"
          },
          "entity": {
            "id": "string",
            "email": "string|null"
          }
        }
      }
    ]
  },
  "error": null
}
```

Payments appear only when the caller is permitted to view them. When an obligor is missing, the `obligor` property is omitted.

---

### GET /api/annuities

**Description**

Lists annuities where the authenticated caller appears as a party (issuer, counterparty, etc.).

**Headers**
- `Authorization: Bearer <JWT>`

**Success Response (200)**

```json
{
  "status": "success",
  "timestamp": "2025-12-01T00:00:00Z",
  "result": [
    {
      "annuity_id": "string",
      "status": "string",
      "deadline": "ISO-8601",
      "relation": "INITIATOR|COUNTERPARTY|..."
    }
  ],
  "error": null
}
```

If the caller has no annuities, `result` is an empty array.

## Example Scripts

Each script accepts environment variables to override defaults (service URLs, credentials, IDs). Run them from the repository root (they handle relative paths).

> Scripts automatically source `.env` (and `.env.local`) from the repository root, as well as a local `.env` in the script directory, before applying their default values.

```bash
cd yieldfabric-docs/annuities
./issue_annuity.sh
./settle_annuity.sh
./get_annuity.sh
./list_annuities.sh
```

### Shared Features

- **Service Health Checks:** Before making API calls, scripts verify that both Auth and Payment services respond (either via `/health` or TCP port).
- **Login Flow:** Scripts call `POST /auth/login/with-services` and extract the JWT token (compatible with multiple response formats).
- **Verbose Output:** Responses are pretty-printed via `jq`, and key steps emit emoji-marked logs for quick scanning.

### Script-Specific Notes

- `issue_annuity.sh`
  - Generates a millisecond timestamp for `annuity_id` and uses it consistently through the issuance flow.
  - Waits for contract tokens/status transitions using the polling utilities inside the issuance handler.

- `issue_workflow.sh`
  - Uses the asynchronous `/api/annuity/issue_workflow` endpoint to start issuance and receive a `workflow_id`.
  - Polls `/api/annuity/issue_workflow/{workflow_id}` until the WorkFlow reaches a terminal state, then prints the final issuance result.

- `issue_polling.sh`
  - A lightweight helper that only polls `/api/annuity/issue_workflow/{workflow_id}` given an existing `workflow_id`.
  - Useful when the initial issuance was triggered elsewhere (e.g., UI) and you just want to track completion from the CLI.

- `settle_annuity.sh`
  - Accepts `ANNUITY_ID` to target the swap created in issuance.
  - Optionally toggles `ACCEPT_PAYMENTS=true` to trigger the accept-all mutation (default matches the handler’s behavior).

- `settle_workflow.sh`
  - Uses the asynchronous `/api/annuity/settle_workflow` endpoint to start settlement and receive a `workflow_id`.
  - Polls `/api/annuity/settle_workflow/{workflow_id}` until the WorkFlow completes, then prints the settlement details.

- `get_annuity.sh`
  - Requires a known `ANNUITY_ID`. Useful for verifying issuance/settlement side-effects without digging into the RDF store.
  - Displays issuer details and payment breakdown, mirroring the handler’s simplified response shape.

- `list_annuities.sh`
  - Shows all annuities where the caller is a party, including their role. Ideal for dashboards or CLI views to list outstanding annuities.

## Adding or Modifying Endpoints

- Register new custom handler modules under `yieldfabric-payments/src/handlers/custom/`, keeping orchestration logic thin and delegating to helper utilities for polling/validation.
- Update the custom handler exports so the rest of the application can mount the new endpoint.
- Wire the route into the payments service router and ensure an example script covers the workflow end to end.
- For documentation, mirror the scripts in `yieldfabric-docs/annuities/` and reference them here so developers have end-to-end samples.

## Troubleshooting

- **Build failures** when adding handlers usually indicate missing exports. Confirm the custom handler module re-exports the new function and that the router mounts it.
- **GraphQL errors** surface through collected messages in the responses; scripts print the raw error strings for faster debugging.
- **Token propagation issues**: ensure `state.schema.execute` receives both `AuthClaims` (core and payments) and the raw JWT string, as done in existing handlers.

With these endpoints and scripts, developers can issue, settle, inspect, and list annuities consistently across services while relying on RabbitMQ-backed processing for asynchronous steps.
