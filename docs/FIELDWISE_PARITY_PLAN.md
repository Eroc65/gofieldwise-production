# FrontDesk Pro vs Fieldwise: Must-Have Delivery Plan

## Objective
FrontDesk Pro will match Fieldwise core operations and ship the next-gen capabilities Fieldwise does not yet provide.

## Capability Matrix

### Core Operations (Fieldwise parity)
- Customer intake: In place (lead intake + customer CRUD) 
- Customer database: In place
- Quotes and quote-to-job: In place (estimates and conversion workflow)
- Scheduling and dispatch: In place (technician assignment, dispatch statuses)
- Job lifecycle and notes: In place (status timeline, notes, completion workflow)
- Invoicing and payments tracking: In place (invoice lifecycle + payment status)
- Follow-ups and reminders: In place (reminder engine, queue, escalation)
- Materials and pricebook: Planned (packages + materials service catalog)
- Marketing landing page: Planned polish pass
- Trial and demo path: In progress
- Mobile PWA: In progress
- Support/help center: In progress

### Beyond Fieldwise (explicitly requested)
- Lead generation and marketing tools: New delivery stream started
- Advertising services control plane: Planned
- Autonomous voice intake (Retell + Twilio): Planned integration track
- Review Harvester: Implemented backend foundation (campaign + launch APIs)
- Re-activation Engine: Implemented backend foundation (campaign + launch APIs)
- Native iOS/Android wrappers: Planned
- Tribal knowledge capture and junior-tech coaching: Planned

## What Was Implemented in This Change
- New marketing campaign domain for owner/admin/dispatcher roles.
- New campaign types:
  - review_harvester
  - reactivation
- New APIs:
  - GET /api/marketing/campaigns
  - POST /api/marketing/campaigns
  - POST /api/marketing/campaigns/{campaign_id}/launch
- Launch execution creates organization-scoped reminder tasks to operationalize outreach immediately.

## Near-Term Build Sequence (next 3 sprints)
1. Sprint M1: Marketing Ops Foundation
- Ship campaign analytics and recipient status tracking.
- Add suppression rules (do-not-contact, recent decline, duplicate prevention windows).
- Add export and audit views for campaign outcomes.

2. Sprint M2: Review Harvester v1
- Post-job review link templates by channel.
- Time-delayed sends based on completion timestamp.
- Response capture webhook and reminder cancellation.

3. Sprint M3: Re-activation Engine v1
- Segment dormant customers by service type and elapsed time.
- Offer templates with booking intent routing.
- Attribution tagging from outreach to booked jobs/invoices.

## Constraints and Safeguards
- All campaign operations are organization-scoped.
- Campaign launch is idempotent at the campaign level (single launch enforced).
- Actions are role-gated to owner/admin/dispatcher.

## Planned Integrations
- Twilio for outbound SMS and response webhooks.
- Retell AI for voice intake handoff into lead + job creation.
- Ad platform connectors for managed campaign visibility (Meta/Google) in later phase.
