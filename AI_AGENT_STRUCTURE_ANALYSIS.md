# AI Agent Structure Analysis

## Current Structure Assessment

### ✅ Strengths

1. **Clear Hierarchy**
   - Wallet → Assets → Denomination → Contracts → Positions
   - Logical grouping that mirrors frontend display

2. **Explicit Relationships**
   - Contract IDs linked to names
   - Payment positions linked to contracts
   - Parties clearly identified

3. **Dual Representation**
   - Both raw values (`rawQuantity`) and formatted values (`formattedAmount`)
   - Enables both calculations and human-readable display

4. **Completeness**
   - All visible frontend information included
   - Metadata (timestamps, IDs, statuses) present

### ⚠️ Potential Issues for AI Agents

1. **Deep Nesting (4-5 levels)**
   ```
   assets.byDenomination[].contractsGroupedByObligation[].positions[]
   ```
   - AI agents may need to traverse many levels to find information
   - Context can be lost in deep nesting

2. **Implicit Relationships**
   - No explicit graph of relationships (e.g., "which contracts are locked in which swaps")
   - Relationships must be inferred from IDs and cross-references

3. **Multiple Views of Same Data**
   - Currency repeated at multiple levels
   - Some duplication (good for context, but can be confusing)

4. **Mixed Abstraction Levels**
   - High-level summaries mixed with low-level balance data
   - No clear separation of "what you can do" vs "current state"

5. **No Semantic Grouping**
   - All position types (cash, credit, obligations) at same level
   - No "actionable items" vs "informational items" distinction

6. **Complex Lock Status Logic**
   - Multiple boolean flags (`lockedInSwap`, `counterpartyLocked`, `collateralInSwap`)
   - Logic is implicit - agent must understand rules

## Recommendations for Improvement

### Option 1: Add Top-Level Summary & Quick Access

```json
{
  "wallet": { ... },
  "quickAccess": {
    "totalPositions": 15,
    "activeContracts": 3,
    "pendingPayments": 8,
    "lockedContracts": 1,
    "currencies": ["AUD", "USD"],
    "netByCurrency": {
      "AUD": -8810.00,
      "USD": 3000.00
    }
  },
  "relationships": {
    "contractToSwaps": {
      "CONTRACT-123": ["SWAP-456"]
    },
    "swapToContracts": {
      "SWAP-456": {
        "initiator": ["CONTRACT-123"],
        "counterparty": ["CONTRACT-789"]
      }
    },
    "positionToContract": {
      "POS-456": "CONTRACT-123"
    }
  },
  "assets": { ... },
  "swaps": { ... }
}
```

### Option 2: Flatten Critical Information

Add a `flatView` section with denormalized critical info:

```json
{
  "flatView": {
    "allPositions": [
      {
        "id": "POS-456",
        "type": "PAYMENT_PAYABLE",
        "contractId": "CONTRACT-123",
        "contractName": "Annuity Stream",
        "amount": -5000.00,
        "currency": "AUD",
        "status": "PENDING",
        "dueDate": "2026-12-01",
        "isLocked": false,
        "lockReason": null,
        "actions": ["VIEW", "ACCEPT"]  // What can be done
      }
    ],
    "allContracts": [...],
    "allSwaps": [...]
  }
}
```

### Option 3: Add Semantic Markers

```json
{
  "semanticGroups": {
    "actionable": {
      "pendingPayments": [...],
      "pendingSwaps": [...],
      "unlockedContracts": [...]
    },
    "informational": {
      "cashBalances": [...],
      "creditPositions": [...],
      "historicalContracts": [...]
    },
    "warnings": {
      "imminentDueCredit": [...],
      "lockedPositions": [...],
      "overduePayments": [...]
    }
  }
}
```

### Option 4: Add Metadata & Hints

```json
{
  "metadata": {
    "structureVersion": "1.0",
    "lastUpdated": "2025-01-20T10:30:00Z",
    "primaryCurrency": "AUD",
    "totalPositions": 15,
    "fieldDescriptions": {
      "lockStatus": "Indicates if contract can be swapped/transferred",
      "imminentDueCredit": "Credit exposure from payments due from self"
    },
    "commonQueries": {
      "findPendingPayments": "assets.byDenomination[].contractsGroupedByObligation[].positions[?status=='PENDING']",
      "findLockedContracts": "assets.byDenomination[].contractsGroupedByObligation[?isLocked==true]"
    }
  }
}
```

## Recommendation: Hybrid Approach

Combine elements from all options:

1. **Keep current structure** - It matches frontend and is complete
2. **Add `quickAccess` section** - High-level summary for fast understanding
3. **Add `relationships` section** - Explicit graph of entity relationships
4. **Add `flatView` for critical items** - Denormalized view of actionable items
5. **Add `metadata` section** - Structure hints and common queries

This gives AI agents:
- **Quick understanding** via `quickAccess`
- **Complete detail** via existing structure
- **Explicit relationships** via `relationships`
- **Easy querying** via `flatView`
- **Context** via `metadata`

## Alternative: Query Parameters

Instead of including everything, use query parameters:

```
GET /api/wallets/{id}/ai-view?include=summary,relationships,flatView&currency=AUD
```

This allows agents to request only what they need, reducing response size and complexity.

