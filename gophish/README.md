# GoPhish integration boundary

The application supports GoPhish through `GophishProvider`, but demo mode defaults to `CAMPAIGN_PROVIDER=mock`.
For a real authorized lab, pre-create exactly these GoPhish resources and keep them scoped to synthetic/test targets:
- Template: `MorphPhish Authorized Simulation`
- Landing page: `MorphPhish Safe Landing`
- Sending profile: `MorphPhish Test SMTP`
- Group: `MorphPhish Synthetic Targets`

Set `GOPHISH_URL`, `GOPHISH_API_KEY`, and `CAMPAIGN_PROVIDER=gophish` only after Rules of Engagement approval.
The application does not ask GoPhish to collect or persist real passwords .

