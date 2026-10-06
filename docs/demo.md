# Demo procedure

1. Start the stack and open `http://localhost:3000`.
2. Show the dashboard: KPI tiles, the engagement funnel (delivered→opened→clicked→submitted→reported), the workforce risk distribution, and the department risk chart.
3. Open Employees and select the Finance persona.
4. Explain deterministic risk factors and synthetic context.
5. Open **Simulations**, select an employee, set an objective/difficulty, and generate a message.
6. Review the generated subject/body/pretext/landing inline; optionally **Edit** or **Regenerate**, then **Approve**.
7. Click **Launch simulation** on the approved card, enter the admin credentials (demo: `root` / `root`) — the campaign is created and sent in one step, and a copyable simulation link appears.
8. With `EMAIL_PROVIDER=smtp`, open the **Mailpit** inbox at `http://localhost:8025` and show the delivered HTML email — branded sender (the impersonated team), realistic styling, and a **call-to-action button** (not a bare link). The button and the From display name are localized per persona (AZ/EN/RU); the address stays the authorized, allow-listed one.
9. Click the button to open the landing at `http://localhost:3000/simulate/<session-id>` — a **realistic corporate sign-in page** with no upfront warning (following the link is itself recorded as the click).
10. Enter a fake value (e.g. `DEMO-ONLY`) and click **Sign in**. The page immediately reveals the **debrief**: it discloses the authorized simulation, confirms nothing typed was stored, and lists the red flags to watch for. (Or click **Report this message as phishing** to see the "you did the right thing" debrief.)
11. Explain that the backend discards the submitted field immediately and stores only the boolean interaction event.
12. Open **Archive** to show finished runs (recipient submitted/reported, or a rejected draft) with filters by outcome, department, language, and difficulty — active runs stay under **Simulations**.
13. Return to Analytics and show the role + department human-risk map: funnel, per-dimension engagement bars, risk distribution, and the accessible metric tables.
13. Open Training Recommendations and show deterministic corrective guidance.
14. Open System to show mock/real provider selection.
15. Open Swagger at `http://localhost:8000/docs`.
16. Close on the ethics framework: point to `docs/roe.md` (authorization, data minimization/pseudonymization, non-punitive use, and the post-campaign debrief).
