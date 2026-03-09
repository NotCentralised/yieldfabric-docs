# Why Key Registration Fails (500 Errors)

When running the payment workflow with `REQUIRE_MANUAL_SIGNATURE=true`, you may see:

- **Register external key failed (500): Database operation failed**
- **Register key with wallet failed (500): Failed to register key with specific wallet**

Here is why these happen and what would need to change to fix them.

---

## 1. Register same key with investor (acceptor) account

**What we do:** Call auth `POST /keys/external` with the acceptor’s JWT and the **same** Ethereum address (public key) already registered for the issuer.

**Why it fails:** In the auth service, the `keypairs` table has a **UNIQUE constraint on `public_key`** (see `yieldfabric-auth/src/database/schema.rs`):

```sql
CREATE TABLE IF NOT EXISTS keypairs (
    ...
    public_key TEXT UNIQUE NOT NULL,
    ...
);
```

So a given Ethereum address can only appear **once** in `keypairs`. The issuer already has a row for that address; inserting another row for the acceptor with the same `public_key` violates the constraint and the DB returns an error, which auth surfaces as “Database operation failed”.

**Ways to fix (auth service):**

- **Option A:** Relax the constraint so the same key can be linked to multiple entities, e.g.:
  - Change to a **composite** unique constraint, e.g. `UNIQUE(entity_type, entity_id, public_key)`, so the same `public_key` can exist for different `(entity_type, entity_id)` (e.g. issuer and acceptor).
  - Or drop the UNIQUE on `public_key` and add a unique index only where you need it (e.g. per-entity uniqueness), depending on your product rules.
- **Option B:** Keep one key record per address and add a separate “key shared with entities” or “key allowed to sign for wallets” table that links that key to multiple users/wallets, and have the rest of the stack (MQ, manual signing) use that table when resolving “who can sign for this wallet”.

---

## 2. Register issuer key with investor (or loan) wallet

**What we do:** Call auth `POST /keys/register-with-specific-wallet` with the **issuer’s** key ID and JWT, and the **acceptor’s** (or loan) wallet address, so that the same key can sign for that wallet.

**Why it can fail:** In the auth service, `register_key_as_wallet_owner_with_address`:

1. Updates the key’s metadata (adds the wallet to `registered_wallets`) — this can succeed.
2. Calls `add_key_as_owner_to_smart_contract(key_address, wallet_address, entity_id, jwt_token)`.

The `entity_id` passed there is the **key owner’s** entity (from the key record), i.e. the **issuer**. So the AddOwner message sent to MQ/vault uses:

- `user_id` = issuer’s entity (for user wallets, `mq_user_id = entity_id`),
- `account_address` = acceptor’s (or loan) wallet address.

So we are effectively saying: “Add this key as owner of **this** wallet, in the context of the **issuer**.” The MQ or the smart contract likely expects the wallet to belong to that same context (or the signer/caller to be the wallet owner). The acceptor’s wallet belongs to the **acceptor**, not the issuer, so the AddOwner flow can fail with a 500 (e.g. “Failed to register key with specific wallet”) when the vault/MQ or contract rejects the operation.

**Ways to fix (auth + possibly MQ/vault):**

- **Option A:** When registering a key with a **specific** wallet address, resolve the **wallet owner** (e.g. from payments or auth) and use that entity’s context for the AddOwner message (and JWT if required), so that “add owner” is done as the wallet owner, while the key can still be owned by the issuer in `keypairs` (if you allow one key to be used by multiple entities as in 1.).
- **Option B:** Allow “cross-entity” key registration in auth/MQ: e.g. an admin or a permitted service can register a key (by key_id) to a wallet that belongs to another entity, with explicit checks and audit.
- **Option C:** Avoid cross-entity use: each entity (issuer, acceptor) has its **own** key record for the same address (requires fixing 1. first), and each entity registers **their** key with their own wallets only.

---

## Summary

| Error | Likely cause | Where to change |
|-------|----------------|------------------|
| Register external key (500): Database operation failed | `keypairs.public_key` is UNIQUE; same address cannot be stored for two entities | Auth DB schema / auth key creation logic |
| Register key with specific wallet (500) | AddOwner is done in key owner’s (issuer) context for a wallet that belongs to another entity (acceptor/loan) | Auth `register_key_as_wallet_owner_with_address` and/or MQ/vault AddOwner handling |

The Python workflow is doing the right thing: it tries to register the same key with the investor account and, when that fails, falls back to linking the issuer’s key to the investor’s wallet. Both paths hit the limits above. Fixing registration requires changes in the **auth service** (and possibly MQ/vault) as described.
