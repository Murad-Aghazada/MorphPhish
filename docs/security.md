# Security design

This repository is for authorized awareness simulation only. Synthetic personas and synthetic operational context are the default data source. Campaigns require explicit review and approval before execution.

The credential-simulation endpoint accepts an optional form value only so tests can prove safe handling. The value is immediately discarded: it is not hashed, logged, forwarded, sent to an LLM/GoPhish, stored in PostgreSQL, or included in audit events. Only `{ "credential_submitted": true }` is stored.

Secrets are environment variables and `.env` is ignored. Audit records contain event names and identifiers only. The LLM receives minimum synthetic attributes and is instructed to return structured simulation content; output is validated for dangerous markers and the landing text must explicitly identify simulation/password safety. Real SMTP is constrained by `AUTHORIZED_EMAIL_DOMAINS`.

Prompt injection risk is reduced by never passing arbitrary employee free-form content, limiting provider input to synthetic structured fields, validating output, and requiring human approval. External HR/SIEM/SOC integrations should be read-only/OAuth-scoped where possible and separately audited.
