# Demo procedure

1. Start the stack and open `http://localhost:3000`.
2. Show the dashboard: KPI tiles, the engagement funnel (delivered→opened→clicked→submitted→reported), the workforce risk distribution, and the department risk chart.
3. Open Employees and select the Finance persona.
4. Explain deterministic risk factors and synthetic context.
5. Open **Simulations**, select an employee, set an objective/difficulty, and generate a message.
6. Review the generated subject/body/pretext/landing inline; optionally **Edit** or **Regenerate**, then **Approve**.
7. Click **Launch simulation** on the approved card, enter the admin credentials (demo: `root` / `root`) — the campaign is created and sent in one step, and a copyable simulation link appears.
8. With `EMAIL_PROVIDER=smtp`, open the **Mailpit** inbox at `http://localhost:8025` and show the delivered simulation email (local stand-in for Mailtrap).
9. Click the link (or copy it) to open `http://localhost:3000/simulate/<session-id>`.
9. Record click/form events. If demonstrating submission, use a clearly fake value such as `DEMO-ONLY`.
10. Explain that the backend immediately discards the submitted field and stores only the boolean event.
11. Record a report event.
12. Return to Analytics and show the role + department human-risk map: funnel, per-dimension engagement bars, risk distribution, and the accessible metric tables.
13. Open Training Recommendations and show deterministic corrective guidance.
14. Open System to show mock/real provider selection.
15. Open Swagger at `http://localhost:8000/docs`.
16. Close on the ethics framework: point to `docs/roe.md` (authorization, data minimization/pseudonymization, non-punitive use, and the post-campaign debrief).
