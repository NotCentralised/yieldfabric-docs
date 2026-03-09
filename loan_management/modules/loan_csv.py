"""Loan CSV parsing: currency/date conversion, safe_get, extract_loan_data."""

import re
from typing import List


def convert_currency_to_wei(currency_str: str) -> str:
    """Convert currency string to wei-like format (18 decimals).
    Input: '$31,817.59' -> Output: '31817590000000000000000'
    """
    cleaned = re.sub(r"[\$,]", "", currency_str)
    amount = float(cleaned)
    wei_amount = int(amount * 10**18)
    return str(wei_amount)


def convert_date_to_iso(date_str: str) -> str:
    """Convert date from M/D/YY format to ISO format.
    Input: '2/12/32' -> Output: '2032-02-12T23:59:59Z'
    """
    parts = date_str.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid date format: {date_str}")
    month, day, year = parts
    year_int = int(year)
    if len(year) == 1:
        year = f"200{year_int}"
    elif len(year) == 2:
        year = f"20{year_int}"
    month = f"{int(month):02d}"
    day = f"{int(day):02d}"
    return f"{year}-{month}-{day}T23:59:59Z"


def safe_get(row: List[str], index: int, default: str = "") -> str:
    """Safely get a value from a CSV row, stripping quotes."""
    if index < len(row):
        return row[index].strip('"')
    return default


def extract_loan_data(row: List[str]) -> dict:
    """Extract all loan data from CSV row into a dictionary (column indices per Wisr header)."""
    data = {
        "loanId": safe_get(row, 0),
        "initialAmount": safe_get(row, 1),
        "rate": safe_get(row, 2),
        "settlement": safe_get(row, 3),
        "maturity": safe_get(row, 4),
        "term": safe_get(row, 5),
        "pmtLeft": safe_get(row, 6),
        "principalOutstanding": safe_get(row, 7),
        "accrued": safe_get(row, 8),
        "fee": safe_get(row, 9),
        "unpaidInt": safe_get(row, 10),
        "currentValue": safe_get(row, 11),
        "arrears": safe_get(row, 12),
        "arrearsBal": safe_get(row, 13),
        "daysLate": safe_get(row, 14),
        "state": safe_get(row, 15),
        "secured": safe_get(row, 16),
        "securityType": safe_get(row, 17),
        "vedaCreditScore": safe_get(row, 18),
        "incomeAmount": safe_get(row, 19),
        "mortgageAmount": safe_get(row, 20),
        "mortgageFrequency": safe_get(row, 21),
        "rentAmount": safe_get(row, 22),
        "rentFrequency": safe_get(row, 23),
        "otherLoanAmount": safe_get(row, 24),
        "otherLoanFrequency": safe_get(row, 25),
        "totalAssets": safe_get(row, 26),
        "totalLiabilities": safe_get(row, 27),
        "employmentMonths": safe_get(row, 28),
        "employmentStatus": safe_get(row, 29),
        "previousEmploymentMonths": safe_get(row, 30),
        "currentAddressState": safe_get(row, 31),
        "currentAddressPostcode": safe_get(row, 32),
        "residencyMonths": safe_get(row, 33),
        "residencyStatus": safe_get(row, 34),
        "maritalStatus": safe_get(row, 35),
        "age": safe_get(row, 36),
        "loanPurpose": safe_get(row, 37),
        "isJointApplication": safe_get(row, 38),
        "creditSenseSupplied": safe_get(row, 39),
        "brokerId": safe_get(row, 40),
        "addedDateLocal": safe_get(row, 41),
        "approvedDateLocal": safe_get(row, 42),
        "occupation": safe_get(row, 43),
        "dateOfBirth": safe_get(row, 44),
        "netSurplusRatio": safe_get(row, 45),
        "surplus": safe_get(row, 46),
        "loanAmountRequested": safe_get(row, 47),
        "termRequested": safe_get(row, 48),
        "rateDiscount": safe_get(row, 49),
        "assignmentDate": safe_get(row, 50),
        "nextPayDate": safe_get(row, 51),
        "paymentFrequency": safe_get(row, 52),
        "pmt": safe_get(row, 53),
        "referrerBroker": safe_get(row, 54),
        "assetCode": safe_get(row, 55),
        "vehicleCategory": safe_get(row, 56),
        "residual": safe_get(row, 57),
        "vehicleAge": safe_get(row, 58),
        "manufacturer": safe_get(row, 59),
        "lvr": safe_get(row, 60),
        "hardship": safe_get(row, 61),
        "extensionReceivable": safe_get(row, 62),
        "remainingLoanTerm": safe_get(row, 63),
        "updatedMaturityDate": safe_get(row, 64),
        "totalTerm": safe_get(row, 65),
    }
    return {k: v for k, v in data.items() if v}
