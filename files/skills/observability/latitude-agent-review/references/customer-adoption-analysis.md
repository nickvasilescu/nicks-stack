# Fleet Adoption and Customer-Usage Analysis

Use this playbook when the question is not merely “is the fleet instrumented?” but “are customers actually using the agents?”

## Evidence ladder

Do not collapse these categories:

1. **Provisioned**: a computer or agent exists in the live fleet inventory.
2. **Emitting**: the service appears in Latitude during the chosen window.
3. **User-active**: a non-maintenance session or direct channel interaction exists.
4. **Operationally used**: captured conversation or tool evidence shows a real domain workflow.
5. **Production adoption**: repeated use or scheduled automation produces a customer-facing or business outcome.

Report a strict lower bound from categories 4-5 and a broader footprint from categories 1-3. Never market the broader number as confirmed adoption.

## Procedure

1. Resolve the live Orgo inventory and the customer Latitude project independently. Current live IDs win over a stale fleet ledger.
2. Choose an explicit UTC window and fetch:
   - raw trace totals with `getTraceAnalytics`;
   - sessions and identified users with `getUsersOverview`;
   - service, userId/channel, and model breakdowns with `queryAnalytics`.
3. Map `serviceNames` to live computer names. Classify each as customer/agency, internal, test, or unknown.
4. Quantify concentration. Always compute the largest internal/flagship service share and cron share. High fleet volume can be almost entirely one internal agent.
5. For service-filtered trace listing, use the plural list field and verify every returned row:
   ```json
   {"filters":{"serviceNames":[{"op":"contains","value":"hermes-<prefix>"}]}}
   ```
   Some Latitude interfaces may silently accept unknown filter keys such as `service` or `serviceName` and return unfiltered data. Check each row's `serviceNames`; if filtering is ignored, use the Latitude CLI and verify again.
6. Inspect representative conversations for the highest-value customer services. Capture the business request, tools used, outcome, and whether the request came from a human channel, API session, cron, curator, or test harness.
7. Attribute fleet-wide signals before describing them as customer problems. Query score/signal occurrences by service. A large semantic failure count may belong entirely to an internal high-volume agent.
8. Compare aggregate APIs before publishing counts. `queryAnalytics count`, raw trace totals, and session totals can differ by grain or missing dimensions. Label each number by its source and grain rather than assuming every “count” is a raw trace count.
9. Report confidence-ranked findings:
   - confirmed operational customer use;
   - credible active-use signal;
   - provisioned/emitting only;
   - unsupported inference.

## Verification checklist

- Live inventory timestamp or status was checked.
- Returned trace rows all match the intended `serviceNames` filter.
- Raw traces, sessions, and users are separately labeled.
- Dominant service and cron shares were calculated.
- At least one representative conversation supports each “confirmed use” claim.
- Fleet-wide reliability signals were broken down by service.
- Sparse one-off telemetry was not presented as sustained adoption.

## MomentumClaw example, July 2026

A four-day review found a 53-computer fleet and dozens of agency-labeled emitters, but approximately 98% of sessions belonged to one internal executive agent and roughly 95% were cron-triggered. Conversation inspection nevertheless confirmed a smaller set of agencies using agents for AMS/NowCerts work, document ingestion, email intake, and scheduled reports. The correct conclusion was “verified early customer usage,” not “scaled adoption.”
