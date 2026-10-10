---
document_id: DOC-SEC-001
title: Identity Verification, Dual-Password Security, and Session Governance Policy
category: Identity and Account Security
document_type: POLICY
version: 2
status: ACTIVE
effective_from: "2024-01-01"
effective_until: "2027-12-31"
classification: INTERNAL
allowed_roles: ["CUSTOMER", "FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]
source: Omerta.ai Information Security & KYC Committee
---

# Section 1: Authentication and Session Management

1.1. Dual-Password Architecture
To insulate customer fund movement from standard portal credential stuffing, Omerta.ai enforces segregation of access and authorization:
- Account Login Password: Used solely for authenticating to the web portal or mobile client to read balances, view statements, and open support tickets.
- Transfer Password: A dedicated, separate secret required exclusively when authorizing outbound money movement or beneficiary additions.
- Compromise of a user's login password does not allow an adversary to drain account funds without the independent transfer password.

1.2. Cryptographic Password Storage
All passwords are salted and hashed using bcrypt with an adaptive work factor (minimum 12 rounds). Plaintext passwords are never logged, cached in memory beyond request duration, or transmitted over unencrypted protocols.

# Section 2: Repeated Failed Password Handling

2.1. 3-Strikes Transfer Password Defense
When authorizing transfers, the system tracks failed password submissions:
- Strike 1: Transfer fails with 401 Unauthorized warning notice.
- Strike 2: Second warning notice indicating that one additional failure will restrict transfer capabilities.
- Strike 3: Account transfer status transitions immediately to BLOCKED. Outbound transfers are halted.
- The session remains active to preserve the user's ability to communicate with support and upload remediation documentation.

2.2. Failed Login Rate Limiting
To prevent automated credential bruteforcing, client IP addresses exhibiting more than 5 failed login attempts per minute are subject to exponential backoff delays and temporary 15-minute rate-limit throttling.

# Section 3: Identity Verification and Egyptian National ID Handling

3.1. Document Submission Requirements
Customers submitting identification documents for registration verification or account unlock must upload high-resolution front and back images of their official government-issued ID (Egyptian National ID card or passport).

3.2. Manual and Automated Verification Criteria
Compliance staff verify the following criteria:
- The 14-digit national identity number matches customer birthdate, gender, and governorate of issue according to standard administrative validation checksums.
- Clear alignment between full customer name on file and name inscribed on the government card.
- Absence of digital tampering, blurred text, or screenshot artifacts.

# Section 4: Device and Session Security

4.1. Hardware Device Fingerprinting
Every client connecting to Omerta.ai transmits telemetry including user-agent strings, canvas rendering signatures, operating platform, and screen metrics. These are synthesized into stable device external IDs (e.g. DEV-1001).

4.2. Localhost and Multi-Account Co-Location
When multiple distinct customer profiles authenticate through the exact same physical hardware device:
- 1 Customer on 1 Device: Standard baseline risk (LOW).
- 2 Customers on 1 Device: Elevated co-location risk (HIGH), common in sharing arrangements or initial mule recruitment.
- 3 or More Customers on 1 Device: Critical syndicate risk (CRITICAL), triggering automated alert generation and supervisory queue review.

# Section 5: Account Recovery and Security Escalation

5.1. Password Reset Workflow
Forgot password requests dispatch a cryptographically signed, single-use JWT link with a 15-minute expiration to the customer's registered email address via SMTP STARTTLS.

5.2. Mandatory Password Rotation Post-Restoration
When compliance officers approve a transfer restoration ticket following an identity verification review, the customer is flagged with `require_transfer_password_change = true`. The user is forced to establish a new transfer password upon their next transaction attempt.
