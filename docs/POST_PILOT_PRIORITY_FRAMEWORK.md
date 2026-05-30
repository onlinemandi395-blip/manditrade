# MandiTrade Post-Pilot Priority Framework

Generated on 2026-05-30 for the first controlled real pilot rollout.

## Current Baseline

- private client flow verified
- RFQ flow verified
- public marketplace flow verified
- SuperAdmin privacy boundaries verified
- automated validation green: `105 passed, 5 skipped`
- recommendation status: `GO`

## Priority Order

### Priority 1: Real User Operational Smoothness

Highest impact. More important than new features.

Goal:
Make the first `5-10` users succeed without confusion.

Focus areas:

#### Manufacturer onboarding polish

- reduce onboarding steps
- improve field grouping
- add save-draft support
- add onboarding progress indicator
- improve validation messages
- use a more guided, WhatsApp-style onboarding tone

#### Client clarity

Clients must clearly understand:

```text
Proposal Order
vs
Confirmed Order
vs
Ledger Due
```

This is especially important for semi-urban usage.

#### Public payment clarity

Public buyers should quickly understand:

```text
Pay
-> submit UTR
-> seller verifies
-> dispatch starts
```

#### RFQ response clarity

Manufacturers should clearly understand:

```text
requested qty
offered qty
offered price
payment terms
delivery expectation
```

### Priority 2: Operational Dashboards

High value.

The runtime architecture is already strong. Operators now need visibility.

#### Manufacturer dashboard should show

```text
Today's orders
Pending confirmations
Pending payments
Low stock
Pending RFQs
Pending ledger dues
Today's dispatches
```

#### SuperAdmin dashboard should show

```text
Active manufacturers
Daily trade volume
Marketplace orders
RFQ volume
Pending disputes
Pending approvals
Overdue ledger totals
```

#### Client dashboard should show

```text
Pending proposals
Approved orders
Pending dues
Delivery status
```

### Priority 3: Payment/Reconciliation Hardening

High risk area.

This is the biggest real-world operational risk before scaling.

#### Add payment verification SOPs

Track:

```text
UTR
verified_by
verified_at
payment screenshot
amount mismatch
duplicate UTR
```

#### Add reconciliation dashboard

Daily:

```text
payments received
payments pending verification
failed verification
duplicate UTR attempts
```

#### Add overdue reminder automation

Current Gmail reminders are a good base.

Next step:

```text
scheduled reminder cadence
```

Example:

```text
T+3
T+7
T+15
```

### Priority 4: Support / Incident Tooling

Medium-high.

Support pain usually expands quickly once real users arrive.

#### Admin support console should track

```text
stuck order
payment issue
inventory mismatch
RFQ dispute
login issue
```

#### Basic dispute status

```text
OPEN
UNDER_REVIEW
RESOLVED
```

#### Action timeline

Every order and RFQ should show:

```text
who did what
when
```

### Priority 5: Rich Reporting

Not urgent.

Do not prioritize yet:

- fancy analytics
- BI dashboards
- advanced charts

Table-first summaries are acceptable for the first pilot.

## First Live Pilot Operational Checklist

### Daily SuperAdmin checks

Morning:

- OAuth status
- Drive runtime
- Gmail runtime
- failed notifications
- dead-letter queue
- pending approvals

Afternoon:

- pending payment verifications
- RFQ response delays
- overdue ledger count

Night:

- backup completion
- failed transactions
- stale locks
- recovery report

### Manufacturer onboarding checklist

Before activating manufacturer:

```text
Google Sign-In verified
Drive connected
categories selected
inventory uploaded
minimum 1 product approved
pricing validated
```

### Client onboarding checklist

Before activating client:

```text
email verified
manufacturer assigned
ledger policy selected
credit limit configured
delivery address confirmed
```

### Payment verification SOP

For every public payment, operator should verify:

```text
UTR exists
amount matches
duplicate UTR not used
correct order linked
payment timestamp reasonable
```

Then:

```text
verify payment
-> create payment event
-> notify buyer
-> release dispatch action
```

### RFQ monitoring SOP

Daily check:

```text
RFQs without responses
RFQs partially fulfilled
RFQs accepted but undelivered
zero-response manufacturers
```

### Incident escalation flow

#### P0

Platform unusable:

- login failure
- Drive failure
- transaction corruption

Response:
Immediate

#### P1

Wrong money, data, or privacy:

- wrong ledger
- privacy leak
- wrong commission

Response:
`< 1 hour`

#### P2

Operational friction:

- confusing UI
- delayed notification
- duplicate action confusion

Response:
same day

#### P3

Cosmetic:

- styling
- spacing
- animation

Response:
later

## Most Important UX Gaps Before Real Users

### 1. Proposal vs Confirmed Order

Biggest confusion risk.

Recommended UI aids:

- large status chips
- timeline
- color coding

Example:

```text
Proposal Sent
Awaiting Manufacturer Confirmation
Confirmed
Payment Pending
Dispatched
Delivered
```

### 2. Ledger Visibility

Semi-urban users think in:

```text
Kitna baki hai?
Kitna diya?
Kab dena hai?
```

Not accounting jargon.

UI should prioritize:

```text
Total Due
Paid
Remaining
Due Date
```

### 3. Public Payment Flow

It should feel extremely simple.

Avoid:

- too many fields
- finance terminology

Ideal:

```text
Pay this UPI
Paste UTR
Done
```

### 4. RFQ Complexity

RFQ screens can become overwhelming.

Primary focus:

- qty
- rate
- delivery
- payment terms

Everything else is secondary.

## Pilot Success Metrics

Track weekly.

### Orders

- successful private client orders
- successful public orders
- RFQs created
- RFQs accepted

### Conversion

- public buyer conversion percentage
- RFQ response rate
- proposal-to-confirmed-order percentage

### Operational

- average payment verification time
- dispatch turnaround time
- overdue ledger percentage

### Stability

- failed transactions
- rollback count
- recovery events
- notification failures

### Trust

- support tickets
- privacy complaints
- payment disputes

## Safety and Compliance Controls

Before scaling beyond pilot, add lightweight policies.

### Data retention

Example:

```text
retain pilot logs for 90 days
```

### Test data cleanup

Never mix:

- pilot dummy data
- real trade data

### Backup drills

Monthly:

```text
simulate restore
```

### Operator access boundaries

Never share:

- admin runtime secrets
- manufacturer Drive tokens

### Audit exports

Support:

```text
export order timeline
export ledger
export RFQ history
```

for disputes.

## Non-Blocking Enhancements Ranking

### High

1. notification triage tooling
2. pilot health dashboard
3. payment reconciliation dashboard

### Medium

4. richer SuperAdmin analytics
5. commission analytics expansion

### Low

6. role constant rename: `platform_admin`
7. demo/seed tooling improvements

## Final Recommendation

Do not scale aggressively yet.

First prove:

```text
5 successful public orders
5 successful private client orders
3 successful RFQs
0 privacy leaks
0 payment mismatches
```

Then expand manufacturer count gradually.
