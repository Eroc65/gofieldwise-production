# Runbooks

## Operator Console
- Access the dashboard at `/apps/console`.
- Use the chat box to submit requests.
- Approve or reject tasks in the approvals queue.
- Monitor live run logs and agent health.

## Adding a Worker
- Add a new folder under `/workers` for the agent.
- Register the worker in the control agent's routing logic.
- Implement domain-specific tools and approval policies.

## Supabase
- Database migrations in `/supabase/migrations`.
- Edge Functions in `/supabase/functions`.
- Store credentials and secrets server-side only.
