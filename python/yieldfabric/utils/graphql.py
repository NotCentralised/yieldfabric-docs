"""
GraphQL helper utilities
"""

from typing import Any, Dict, List, Optional


class GraphQLMutation:
    """Helper class for building GraphQL mutations."""
    
    DEPOSIT = """
    mutation Deposit($input: DepositInput!) {
        deposit(input: $input) {
            success
            message
            accountAddress
            depositResult
            messageId
            timestamp
        }
    }
    """
    
    WITHDRAW = """
    mutation Withdraw($input: WithdrawInput!) {
        withdraw(input: $input) {
            success
            message
            accountAddress
            withdrawResult
            messageId
            timestamp
        }
    }
    """
    
    INSTANT = """
    mutation Instant($input: InstantInput!) {
        instant(input: $input) {
            success
            message
            accountAddress
            destinationId
            idHash
            messageId
            paymentId
            sendResult
            timestamp
        }
    }
    """
    
    ACCEPT = """
    mutation Accept($input: AcceptInput!) {
        accept(input: $input) {
            success
            message
            accountAddress
            idHash
            acceptResult
            messageId
            timestamp
        }
    }
    """
    
    CREATE_OBLIGATION = """
    mutation CreateObligation($input: CreateObligationInput!) {
        createObligation(input: $input) {
            success
            message
            accountAddress
            obligationResult
            messageId
            contractId
            transactionId
            signature
            timestamp
            idHash
        }
    }
    """
    
    ACCEPT_OBLIGATION = """
    mutation AcceptObligation($input: AcceptObligationInput!) {
        acceptObligation(input: $input) {
            success
            message
            accountAddress
            obligationId
            acceptResult
            messageId
            transactionId
            signature
            timestamp
        }
    }
    """
    
    TRANSFER_OBLIGATION = """
    mutation TransferObligation($input: TransferObligationInput!) {
        transferObligation(input: $input) {
            success
            message
            accountAddress
            obligationId
            destinationId
            destinationAddress
            transferResult
            messageId
            transactionId
            signature
            timestamp
        }
    }
    """
    
    CANCEL_OBLIGATION = """
    mutation CancelObligation($input: CancelObligationInput!) {
        cancelObligation(input: $input) {
            success
            message
            accountAddress
            obligationId
            cancelResult
            messageId
            transactionId
            signature
            timestamp
        }
    }
    """
    
    CREATE_OBLIGATION_SWAP = """
    mutation CreateObligationSwap($input: CreateObligationSwapInput!) {
        createObligationSwap(input: $input) {
            success
            message
            swapId
            accountAddress
            counterpartyAddress
            swapResult
            messageId
            timestamp
        }
    }
    """
    
    CREATE_PAYMENT_SWAP = """
    mutation CreatePaymentSwap($input: CreatePaymentSwapInput!) {
        createPaymentSwap(input: $input) {
            success
            message
            swapId
            accountAddress
            counterpartyAddress
            swapResult
            messageId
            timestamp
        }
    }
    """
    
    CREATE_SWAP = """
    mutation CreateSwap($input: CreateSwapInput!) {
        createSwap(input: $input) {
            success
            message
            swapId
            accountAddress
            counterpartyAddress
            swapResult
            messageId
            timestamp
        }
    }
    """
    
    COMPLETE_SWAP = """
    mutation CompleteSwap($input: CompleteSwapInput!) {
        completeSwap(input: $input) {
            success
            message
            swapId
            accountAddress
            completeResult
            messageId
            timestamp
        }
    }
    """
    
    CANCEL_SWAP = """
    mutation CancelSwap($input: CancelSwapInput!) {
        cancelSwap(input: $input) {
            success
            message
            swapId
            accountAddress
            cancelResult
            messageId
            timestamp
        }
    }
    """
    
    MINT = """
    mutation Mint($input: MintInput!) {
        mint(input: $input) {
            success
            message
            accountAddress
            mintResult
            messageId
            timestamp
        }
    }
    """
    
    BURN = """
    mutation Burn($input: BurnInput!) {
        burn(input: $input) {
            success
            message
            accountAddress
            burnResult
            messageId
            timestamp
        }
    }
    """
    
    @staticmethod
    def get_mutation(mutation_name: str) -> Optional[str]:
        """Get mutation string by name."""
        mutations = {
            'deposit': GraphQLMutation.DEPOSIT,
            'withdraw': GraphQLMutation.WITHDRAW,
            'instant': GraphQLMutation.INSTANT,
            'accept': GraphQLMutation.ACCEPT,
            'create_obligation': GraphQLMutation.CREATE_OBLIGATION,
            'accept_obligation': GraphQLMutation.ACCEPT_OBLIGATION,
            'transfer_obligation': GraphQLMutation.TRANSFER_OBLIGATION,
            'cancel_obligation': GraphQLMutation.CANCEL_OBLIGATION,
            'create_obligation_swap': GraphQLMutation.CREATE_OBLIGATION_SWAP,
            'create_payment_swap': GraphQLMutation.CREATE_PAYMENT_SWAP,
            'create_swap': GraphQLMutation.CREATE_SWAP,
            'complete_swap': GraphQLMutation.COMPLETE_SWAP,
            'cancel_swap': GraphQLMutation.CANCEL_SWAP,
            'mint': GraphQLMutation.MINT,
            'burn': GraphQLMutation.BURN,
        }
        return mutations.get(mutation_name)
    
    @staticmethod
    def build_payload(mutation: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Build GraphQL payload."""
        return {
            'query': mutation,
            'variables': variables
        }


class GraphQLQuery:
    """Helper class for building GraphQL queries."""
    
    @staticmethod
    def build_payload(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build GraphQL query payload."""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        return payload

