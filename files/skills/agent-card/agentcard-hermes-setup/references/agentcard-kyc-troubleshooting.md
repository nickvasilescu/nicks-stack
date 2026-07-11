# AgentCard KYC Troubleshooting

Use this reference when AgentCard identity verification (document / face) is incomplete or links fail. For wallet funding after KYC already shows approved, prefer `references/agentcard-wallet-funding.md`.

## Ground truth from the MCP flow

- `get_wallet` may provision an active wallet but funding can still return `Verification is required before funding the wallet`.
- `submit_user_info` stores the phone number and cardholder terms; it is separate from document/face KYC. Do both when the product asks.
- `get_kyc_status` and `start_kyc` return the current `nextStep`, missing fields, and fresh upload/verification URLs.
- For US documents, the missing tax field is `ssn`; it is forwarded to the verification provider and should not be stored in memory or support messages.
- When `get_kyc_status` is already `verified`/`approved` and `fund_wallet` still fails verification, do **not** re-collect ID/SSN. Follow the post-KYC section in `references/agentcard-wallet-funding.md` and escalate to support if phone+terms are already saved.

## Preferred KYC flow

1. Call `get_kyc_status` or `start_kyc(terms_accepted=true)`.
2. Tell the user AgentCard will read a government ID photo and they will confirm extracted values before submission.
3. Do not ask what document type/country up front. The KYC flow detects it from the photo.
4. If the platform exposes image bytes directly, use `submit_kyc_document` with `front_base64` and optional `back_base64`.
5. If the platform only provides local cache file paths and `submit_kyc_document(file_path=...)` says the MCP connection is remote, do not stop. Use the upload URL token from the MCP result with a direct HTTPS POST from the local shell:

```python
import requests
from pathlib import Path

base = 'https://api.agentcard.sh/kyc/document'
token = '<token from uploadUrl query parameter>'
for side, path in [('front', '/path/to/front.jpg'), ('back', '/path/to/back.jpg')]:
    r = requests.post(
        base,
        params={'token': token, 'side': side},
        headers={'Content-Type': 'image/jpeg'},
        data=Path(path).read_bytes(),
        timeout=60,
    )
    print(side, r.status_code, r.text[:1000])
```

6. After both sides upload, call `check_kyc_document`.
7. Show the extracted non-sensitive fields to the user for confirmation. Do not repeat or persist SSN.
8. Collect only fields requested by AgentCard. For US users, ask for 9-digit SSN only when `missingFields` includes `ssn`.
9. Call `submit_kyc_fields` with the SSN and corrections if any.
10. If the final face verification URL fails immediately as expired, call `start_kyc(terms_accepted=true)` once for a fresh link and instruct the user to open it in Safari/Chrome, not an in-app browser.
11. If fresh face-scan links still say expired immediately, open AgentCard support with the KYC state and failure symptoms. Do not include raw SSN or ID images/details in support messages.
12. After KYC shows approved, ensure `submit_user_info` (phone + terms) if not already done, then fund via `fund_wallet` per `references/agentcard-wallet-funding.md`.

## Expired-link failure pattern

Observed pattern:

- Upload-only or verify links can show `Verification link expired` immediately in the user's browser, even when generated fresh.
- Direct upload to `/kyc/document?token=...&side=front|back` using the upload token can still succeed and advance the KYC document state.
- The face-scan step may remain blocked if `/kyc/verify` links immediately expire. At that point support intervention or KYC session reset is the right path.

## Support escalation templates

Face-scan links expired:

```text
KYC face verification links are immediately showing "Verification link expired" for the user, even when freshly generated via start_kyc. The account has already collected ID document and SSN, and get_kyc_status reports pending with only face scan remaining. The user also tried opening the fresh link in an external browser outside the messaging app's in-app browser. Please provide an alternate way to complete face verification or reset/fix the KYC session.
```

KYC already approved but wallet onramp still blocked: use the funding template in `references/agentcard-wallet-funding.md` (do not re-send documents/SSN).

## Privacy rules

- Never save SSN, document number, full address, or raw ID images to memory.
- Do not include SSN or raw ID details in email/support escalation.
- It is acceptable to retain non-sensitive process lessons in this reference, but not one user's KYC artifacts.
