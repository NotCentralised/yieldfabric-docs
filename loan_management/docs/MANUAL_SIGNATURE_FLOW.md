# Manual signature flow for messages

This document describes how the **manual** signature flow works in the app, based on `yieldfabric-app/src/components/actions/SignaturePreviewDrawer.tsx` and related services.

**Linking Python:** To have Python trigger an operation that then requires manual signing in the app, see [LINKING_PYTHON_TO_MANUAL_SIGNATURE.md](./LINKING_PYTHON_TO_MANUAL_SIGNATURE.md).

## When the flow is used

- The message must have **execution mode = Manual** (`message.execution_mode === 'Manual'`). Automatic messages do not open the drawer for manual sign.
- The message must be in a signable state:
  - `message.response?.status === 'manual_signature'`, or
  - `message.executing === true`, or
  - `message.response?.success === false` (retry after failure).
- The drawer shows only if the message is **not** already successfully executed.

## High-level steps

1. **Load unsigned transaction** – Get the data to sign and the **message hash** from the backend.
2. **Load keys** – Fetch user/group keys and let the user pick one.
3. **Sign** – Either with **MetaMask** (external key) or with the **auth key-operations API** (internal key).
4. **Submit signature** – Send the signature back to the messages API.

---

## 1. Loading the unsigned transaction

- **API:** `GET /api/users/:userId/messages/:messageId/unsigned-transaction`
- **Service:** `messagesService.getUnsignedTransaction(userId, message.id)`
- **Response:** Object that must include:
  - `message_hash` – Hex string (with or without `0x`) used as the payload to sign. **Required for signing.**
  - Other fields: `id`, `source`, `account_address`, `chain_id`, `context`, optional `transactions`, etc.
- **Failed messages (retry):** If `message.response?.success === false`, the drawer builds a **mock** unsigned transaction from `message.data` (no backend call for the initial load). When the user clicks Sign, it still fetches the unsigned transaction from the backend to get `message_hash` for consistency.

---

## 2. Loading keys

- **User:** `keysService.getUserKeyPairs(userId)` → `GET /keys/users/:userId/keys`
- **Group:** `keysService.getGroupKeyPairs(userId)` → `GET /keys/auth/groups/:groupId/keypairs`
- Only **active** keys are shown. For users, if none are active, the app tries `getUserDefaultKeyPair(userId)`.
- User selects one key; that key is used for the next sign step.

---

## 3. Signing (two paths)

### A. External key (MetaMask)

- **When:** `selectedKey.provider_type === 'External' && selectedKey.key_type === 'External'`.
- **Payload:** The **raw message hash** as hex:
  - `messageToSign = messageHashHex.startsWith('0x') ? messageHashHex : '0x' + messageHashHex`
- **API:** No backend sign call. The app calls:
  - `keysService.signMessageWithMetaMask(messageToSign, selectedKey.public_key)`
- **Implementation of `signMessageWithMetaMask`:** Uses `window.ethereum.request({ method: 'personal_sign', params: [message, account] })`. So MetaMask signs the **hex string** (treated as a UTF-8 message by `personal_sign`). The backend/MQ will later recover the signer from this signature and the same message hash.
- **Result:** `signatureHex` (hex string, typically with `0x`).

### B. Internal key (OpenSSL/HSM/Hybrid)

- **Payload:** The message hash is turned into an **Ethereum Signed Message** form:
  - Decode `messageHashHex` to 32 bytes.
  - Build: `prefix = "\x19Ethereum Signed Message:\n32"` then `prefixedMessage = prefix || messageHashBytes`.
  - Hash with **Keccak256**: `prefixedHash = keccak256(prefixedMessage)`.
- **API:** `keysService.signData(signRequest)` → `POST /key-operations/sign` with:
  - `key_id`, `entity_type`, `entity_id`, `data: prefixedHash`, `data_format: 'hex'`, `provider_type`.
- **Response:** `signResponse.result` (hex or base64) and `signResponse.result_format`. The drawer normalizes to hex with `0x` prefix.
- **Result:** `signatureHex`.

So for internal keys the app signs the **Keccak256 hash of the Ethereum Signed Message prefix + 32-byte message hash**; for MetaMask it sends the **raw message hash hex** to `personal_sign`.

---

## 4. Submitting the signature

- **API:** `POST /api/users/:userId/messages/:messageId/submit-signed-message`
- **Body:** `{ signature: signatureHex }`
- **Service:** `messagesService.confirmSignature(userId, message.id, signatureHex)`
- **Retry path:** If the unsigned transaction had `source === 'retry'`, the app first calls `messagesService.retryFailedMessage(userId, message.id, ExecutionMode.Manual)` and then `confirmSignature(...)`.

After a successful `confirmSignature`, the drawer calls `onSignatureConfirmed()` so the parent can refresh or close.

---

## Data flow summary

```
Message (Manual, status manual_signature or executing or failed)
    → GET unsigned-transaction  →  { message_hash, ... }
    → User selects key (user or group keys)
    → If External: personal_sign(message_hash_hex) via MetaMask  →  signatureHex
    → If Internal: prefix+hash then POST /key-operations/sign     →  signatureHex
    → POST submit-signed-message  { signature: signatureHex }
    → onSignatureConfirmed()
```

---

## Relevant API endpoints (app → backend)

| Step              | Method | Path                                                                 | Notes                          |
|-------------------|--------|----------------------------------------------------------------------|--------------------------------|
| Unsigned tx       | GET    | `/api/users/:userId/messages/:messageId/unsigned-transaction`       | Must return `message_hash`     |
| Submit signature  | POST   | `/api/users/:userId/messages/:messageId/submit-signed-message`       | Body: `{ signature }`          |
| User keys         | GET    | `/keys/users/:userId/keys`                                           | For key picker                 |
| Group keys        | GET    | `/keys/auth/groups/:groupId/keypairs`                                | For key picker                 |
| Sign (internal)   | POST   | `/key-operations/sign`                                               | For non-external keys only     |

MetaMask signing is done entirely in the browser via `window.ethereum`; no sign API is called for external keys.

---

## Message hash format

- The **backend** (or MQ) is responsible for producing the same `message_hash` that will be used for verification (e.g. `ecrecover(message_hash, signature)` or equivalent).
- The drawer **never** recomputes the message hash from transaction data; it always uses `message_hash` from `getUnsignedTransaction`.
- For **internal** keys the app hashes with the Ethereum Signed Message prefix before sending to `/key-operations/sign`. For **MetaMask** it passes the raw `message_hash` hex to `personal_sign`. Backend/MQ must therefore:
  - Either expect the same prefixed hash for both paths, or
  - Accept the raw hash for MetaMask and treat it consistently when verifying (e.g. same prefix applied server-side for verification).
