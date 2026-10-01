import React, { useEffect, useState, useCallback, useContext, createContext } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, NavLink, useParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { api } from './api';
import './styles.css';

/* ------------------------------------------------------------------ theme */
const ThemeCtx = createContext({ theme: 'light', toggle: () => {} });
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') || 'light');
  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('mp-theme', next); } catch { /* private mode */ }
      return next;
    });
  }, []);
  return <ThemeCtx.Provider value={{ theme, toggle }}>{children}</ThemeCtx.Provider>;
}

/* ------------------------------------------------------------------ toasts */
const ToastCtx = createContext(() => {});
const useToast = () => useContext(ToastCtx);
function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = useCallback((text, kind = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setItems((v) => [...v, { id, text, kind }]);
    setTimeout(() => setItems((v) => v.filter((t) => t.id !== id)), 4200);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts">{items.map((t) => <div key={t.id} className={'toast ' + t.kind}>{t.text}</div>)}</div>
    </ToastCtx.Provider>
  );
}

/* ------------------------------------------------------------------ helpers */
function useLoad(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    setData(null); setError('');
    api(path).then((d) => live && setData(d)).catch((x) => live && setError(x.message));
    return () => { live = false; };
  }, [path]);
  return [data, error, setData];
}
const titleCase = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
const riskColor = (score) => score < 35 ? 'var(--risk-low)' : score < 65 ? 'var(--risk-medium)' : score < 85 ? 'var(--risk-high)' : 'var(--risk-critical)';
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const Load = () => <div className="stack"><div className="skeleton" /><div className="skeleton" /></div>;
const Err = ({ e }) => <div className="error"><b>Something went wrong.</b> {e}</div>;
const Empty = ({ children }) => <div className="empty">{children}</div>;

function Metric({ label, value, unit, fill }) {
  return (
    <div className="card metric">
      <span className="label">{label}</span>
      <span className="value">{value}{unit && <span className="unit">{unit}</span>}</span>
      {fill != null && <div className="spectrum"><i style={{ width: Math.max(0, Math.min(100, fill)) + '%' }} /></div>}
    </div>
  );
}
const Badge = ({ kind, children }) => <span className={'badge ' + (kind || '')}>{children}</span>;

/* ------------------------------------------------------------------ brand + nav */
function Glyph() {
  return (
    <svg className="glyph" viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="mp-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4b4ded" />
          <stop offset="1" stopColor="#12b5a5" />
        </linearGradient>
      </defs>
      <rect x="3" y="3" width="26" height="26" rx="9" fill="url(#mp-g)" />
      <path d="M8 21c3-9 13-9 16 0" fill="none" stroke="#fff" strokeWidth="2.3" strokeLinecap="round" />
      <circle cx="16" cy="11.5" r="2.1" fill="#fff" />
    </svg>
  );
}
const pages = [
  ['/', 'Dashboard'], ['/employees', 'Employees'], ['/simulations', 'Simulations'],
  ['/analytics', 'Analytics'], ['/recommendations', 'Training'], ['/status', 'System'],
];
function ModeChip() {
  const [h] = useLoad('/health');
  const mock = h && h.mode && Object.values(h.mode).every((v) => v === 'mock');
  return (
    <span className="modechip">
      <span className="dot" style={mock === false ? { background: 'var(--risk-medium)', boxShadow: '0 0 0 3px color-mix(in srgb, var(--risk-medium) 22%, transparent)' } : undefined} />
      {h ? (mock ? 'synthetic · mock mode' : 'live providers') : 'connecting…'}
    </span>
  );
}
function ThemeToggle() {
  const { theme, toggle } = useContext(ThemeCtx);
  const dark = theme === 'dark';
  return (
    <button className="themeToggle" onClick={toggle} aria-label="Toggle color theme">
      <span>{dark ? 'Dark' : 'Light'} theme</span>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        {dark
          ? <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" />
          : <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" /></>}
      </svg>
    </button>
  );
}
function Layout({ children }) {
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <div className="wordmark"><Glyph />MorphPhish</div>
          <div className="morphline" />
          <div className="tag">role-aware phishing simulation</div>
        </div>
        <nav className="side">
          {pages.map(([to, label]) => <NavLink key={to} to={to} end={to === '/'}>{label}</NavLink>)}
        </nav>
        <div className="side-foot">
          <ModeChip />
          <ThemeToggle />
        </div>
      </aside>
      <main><div className="page">{children}</div></main>
    </div>
  );
}
const Head = ({ eyebrow, title, sub }) => (
  <div className="pagehead">
    {eyebrow && <div className="eyebrow">{eyebrow}</div>}
    <h1>{title}</h1>
    {sub && <p className="muted">{sub}</p>}
  </div>
);

/* ------------------------------------------------------------------ dashboard */
function DeptChart({ data }) {
  const { theme } = useContext(ThemeCtx); // re-read colors on theme change
  const grid = cssVar('--border'); const muted = cssVar('--muted');
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} key={theme}>
        <XAxis dataKey="department" interval={0} tick={{ fill: muted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: grid }} />
        <YAxis domain={[0, 100]} tick={{ fill: muted, fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip cursor={{ fill: 'color-mix(in srgb, var(--iris) 8%, transparent)' }}
          contentStyle={{ background: cssVar('--surface'), border: '1px solid ' + grid, borderRadius: 12, color: cssVar('--ink'), fontSize: 13 }} />
        <Bar dataKey="average_risk" radius={[6, 6, 0, 0]} maxBarSize={54}>
          {data.map((d, i) => <Cell key={i} fill={riskColor(d.average_risk)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
function Dashboard() {
  const [a, e] = useLoad('/analytics');
  if (e) return <Err e={e} />;
  if (!a) return <Load />;
  return (
    <>
      <section className="hero">
        <div className="eyebrow">Human-risk telemetry</div>
        <h1>Phishing that <span className="morphword">morphs</span> to every role — measured, not guessed.</h1>
        <p>Generate role-aware lures on synthetic personas, review and approve each one, then watch how your organization responds — all in a fully isolated lab.</p>
      </section>
      <section className="grid4" style={{ marginTop: 16 }}>
        <Metric label="Delivery" value={a.delivery_rate} unit="%" fill={a.delivery_rate} />
        <Metric label="Click rate" value={a.click_rate} unit="%" fill={a.click_rate} />
        <Metric label="Submission" value={a.submission_rate} unit="%" fill={a.submission_rate} />
        <Metric label="Reported" value={a.reporting_rate} unit="%" fill={a.reporting_rate} />
      </section>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Average risk by department</h3><Badge kind="iris">0–100 scale</Badge></div>
        {a.by_department && a.by_department.length ? <DeptChart data={a.by_department} /> : <Empty>No department data yet.</Empty>}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ employees */
function Employees() {
  const [d, e, setD] = useLoad('/employees');
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const sync = async () => {
    setBusy(true);
    try {
      const r = await api('/hr/sync', { method: 'POST' });
      setD(await api('/employees'));
      toast(`Synced from ${r.provider}: ${r.created} added, ${r.updated} updated.`, 'ok');
    } catch (x) { toast(x.message, 'err'); }
    setBusy(false);
  };
  if (e) return <Err e={e} />;
  return (
    <>
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <Head eyebrow="Personas from the HR data layer" title="Employees" sub="Role, department, and language drive each persona's risk profile." />
        <button className="secondary" onClick={sync} disabled={busy}>{busy ? 'Syncing…' : 'Sync from HR'}</button>
      </div>
      {!d ? <Load /> : (
        <div className="card" style={{ padding: 8 }}>
          <table>
            <thead><tr><th>Name</th><th>Department</th><th>Role</th><th>Lang</th><th>Source</th><th /></tr></thead>
            <tbody>
              {d.map((x) => (
                <tr key={x.id}>
                  <td style={{ fontWeight: 600 }}>{x.full_name}</td>
                  <td>{x.department}</td>
                  <td className="muted">{x.role}</td>
                  <td className="mono">{x.preferred_language}</td>
                  <td><span className="badge" title={x.external_id || ''}>{x.source}</span></td>
                  <td style={{ textAlign: 'right' }}><NavLink to={`/employees/${x.id}`}>View →</NavLink></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
function Employee() {
  const { id } = useParams();
  const [p, er] = useLoad('/employees/' + id + '/profile');
  if (er) return <Err e={er} />;
  if (!p) return <Load />;
  const { employee: e, risk: r, context: c } = p;
  const max = Math.max(1, ...r.factors.map((f) => f.points));
  return (
    <>
      <Head eyebrow={e.department + ' · ' + e.role} title={e.full_name} />
      <section className="grid2">
        <div className="card">
          <h3>Persona</h3>
          <div className="scen">
            <div className="field"><b>Department</b><p>{e.department}</p></div>
            <div className="field"><b>Role</b><p>{e.role}</p></div>
            <div className="field"><b>Preferred language</b><p className="mono">{e.preferred_language}</p></div>
            <div className="field"><b>HR source</b><p><span className="badge">{e.source}</span> <span className="mono muted">{e.external_id}</span></p></div>
          </div>
        </div>
        <div className="card">
          <h3>Risk profile</h3>
          <div className="riskhead">
            <span className="score" style={{ color: riskColor(r.score) }}>{r.score}<small>/100</small></span>
            <Badge kind={r.level}>{r.level}</Badge>
          </div>
          <div style={{ marginTop: 16 }}>
            {r.factors.map((f) => (
              <div className="factor" key={f.key}>
                <span className="fname">{f.label}<small className="muted"> · {f.detail}</small></span>
                <span className="ftrack"><i style={{ width: (f.points / max * 100) + '%' }} /></span>
                <span className="fval">{f.points}</span>
              </div>
            ))}
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>Weighted across role, department, language, data access, and social exposure.</p>
        </div>
      </section>
      <div className="card">
        <h3>Synthetic operational context</h3>
        {c.map((x) => (
          <div className="scen" key={x.id} style={{ paddingBottom: 6 }}>
            <div className="field"><b>{x.kind} · {x.title}</b><p>{x.summary}</p>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                {x.metadata_json.ticket_id && <span className="badge mono">{x.metadata_json.ticket_id}</span>}
                {x.metadata_json.priority && <span className={'badge ' + (x.metadata_json.priority === 'high' ? 'high' : 'medium')}>{x.metadata_json.priority}</span>}
                {x.metadata_json.due_in_days != null && <span className="badge">due in {x.metadata_json.due_in_days}d</span>}
                {x.metadata_json.in_days != null && <span className="badge">in {x.metadata_json.in_days}d</span>}
                {x.metadata_json.channel && <span className="badge mono">{x.metadata_json.channel}</span>}
                {x.metadata_json.thread_count != null && <span className="badge">{x.metadata_json.thread_count} threads · {x.metadata_json.participants} people</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ simulations */
const EDITABLE = new Set(['REVIEW_REQUIRED', 'GENERATED', 'DRAFT']);
function ScenarioCard({ s, onChange }) {
  const toast = useToast();
  const [edit, setEdit] = useState(false);
  const [f, setF] = useState({ subject: s.subject, email_body: s.email_body, pretext: s.pretext, landing_page_message: s.landing_page_message });
  const [launch, setLaunch] = useState(null);
  const [auth, setAuth] = useState(false);
  const [cred, setCred] = useState({ u: '', p: '' });
  const editable = EDITABLE.has(s.status);
  const run = async (fn, ok) => { try { const r = await fn(); if (ok) toast(ok, 'ok'); onChange(); return r; } catch (x) { toast(x.message, 'err'); } };
  const save = () => run(async () => { await api(`/scenarios/${s.id}`, { method: 'PATCH', body: JSON.stringify(f) }); setEdit(false); }, 'Message updated.');
  const act = (path, ok) => run(() => api(`/scenarios/${s.id}/${path}`, { method: 'POST' }), ok);
  // Regenerate updates THIS scenario in place (no new card).
  const regen = () => run(() => api(`/scenarios/${s.id}/regenerate`, { method: 'POST' }), 'Scenario regenerated.');
  const doLaunch = async () => {
    const auth64 = btoa(`${cred.u}:${cred.p}`);
    const r = await run(() => api(`/scenarios/${s.id}/launch`, { method: 'POST', headers: { Authorization: 'Basic ' + auth64 }, body: JSON.stringify({}) }), 'Simulation launched.');
    if (r) { setLaunch(r); setAuth(false); setCred({ u: '', p: '' }); }
  };
  return (
    <div className="card scen">
      <div className="row"><h3 style={{ margin: 0, maxWidth: '70%' }}>{s.subject}</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {s.quality_score != null && <Badge kind={s.quality_score >= 80 ? 'low' : s.quality_score >= 50 ? 'medium' : 'high'} title="Automated quality score">Q {Math.round(s.quality_score)}</Badge>}
          <Badge kind={'status-' + s.status.toLowerCase()}>{s.status.replace('_', ' ')}</Badge>
        </div>
      </div>
      {s.quality_notes && s.quality_notes.length > 0 && EDITABLE.has(s.status) &&
        <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>Review notes: {s.quality_notes.join(' · ')}</p>}
      {edit ? (
        <div className="editform">
          <label>Subject</label>
          <input value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} />
          <label>Email body</label>
          <textarea rows={4} value={f.email_body} onChange={(e) => setF({ ...f, email_body: e.target.value })} />
          <label>Pretext (cover story)</label>
          <textarea rows={2} value={f.pretext} onChange={(e) => setF({ ...f, pretext: e.target.value })} />
          <label>Landing page — must contain the words “simulation” and “password”</label>
          <textarea rows={2} value={f.landing_page_message} onChange={(e) => setF({ ...f, landing_page_message: e.target.value })} />
          <div className="actions"><button onClick={save}>Save changes</button><button className="secondary" onClick={() => setEdit(false)}>Cancel</button></div>
        </div>
      ) : (
        <>
          <div className="field"><b>Email body</b><p>{s.email_body}</p></div>
          <div className="field"><b>Pretext</b><p>{s.pretext}</p></div>
          <div className="field"><b>Landing page</b><p>{s.landing_page_message}</p></div>
          {s.risk_indicators && s.risk_indicators.length > 0 &&
            <p className="muted" style={{ fontSize: 13 }}>Risk cues: {s.risk_indicators.join(' · ')}</p>}
        </>
      )}
      {!edit && (
        <div className="actions">
          {editable && <button className="secondary" onClick={() => setEdit(true)}>Edit</button>}
          {editable && <button className="secondary" onClick={regen}>Regenerate</button>}
          {s.status === 'REVIEW_REQUIRED' && <button onClick={() => act('approve', 'Scenario approved.')}>Approve</button>}
          {editable && <button className="ghost" onClick={() => act('reject', 'Scenario rejected.')}>Reject</button>}
          {s.status === 'APPROVED' && !auth && <button onClick={() => setAuth(true)}>Launch simulation</button>}
        </div>
      )}
      {!edit && auth && (
        <div className="editform" style={{ maxWidth: 360 }}>
          <label>Admin sign-in required to launch</label>
          <input placeholder="username" value={cred.u} onChange={(e) => setCred({ ...cred, u: e.target.value })} />
          <input placeholder="password" type="password" value={cred.p} onChange={(e) => setCred({ ...cred, p: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && doLaunch()} />
          <div className="actions">
            <button disabled={!cred.u || !cred.p} onClick={doLaunch}>Confirm &amp; launch</button>
            <button className="secondary" onClick={() => { setAuth(false); setCred({ u: '', p: '' }); }}>Cancel</button>
          </div>
          <span className="muted" style={{ fontSize: 12 }}>Demo credentials: root / root</span>
        </div>
      )}
      {launch && (
        <div className="linkout">
          <span className="mono" style={{ fontSize: 12 }}>SENT →</span>
          <code>{launch.simulation_url}</code>
          <button className="secondary" onClick={() => { navigator.clipboard && navigator.clipboard.writeText(launch.simulation_url); toast('Link copied.', 'ok'); }}>Copy link</button>
          <a href={launch.simulation_url} target="_blank" rel="noreferrer">Open</a>
        </div>
      )}
    </div>
  );
}
function Simulations() {
  const [scen, e, setScen] = useLoad('/scenarios');
  const [emps] = useLoad('/employees');
  const toast = useToast();
  const [emp, setEmp] = useState('');
  const [obj, setObj] = useState('Recognize contextual social-engineering cues');
  const [diff, setDiff] = useState('medium');
  const [lang, setLang] = useState('');
  const [busy, setBusy] = useState(false);
  const refresh = async () => setScen(await api('/scenarios'));
  const gen = async () => {
    setBusy(true);
    try {
      await api('/scenarios/generate', { method: 'POST', body: JSON.stringify({ employee_id: emp, objective: obj, difficulty: diff, language: lang || undefined }) });
      await refresh();
      toast('Message generated — review it below.', 'ok');
    } catch (x) { toast(x.message, 'err'); }
    setBusy(false);
  };
  if (e) return <Err e={e} />;
  return (
    <>
      <Head eyebrow="Generate → review → approve → launch" title="Simulations" sub="Every message is drafted on synthetic data and must be approved before it can be sent." />
      <div className="card form">
        <select value={emp} onChange={(x) => setEmp(x.target.value)}>
          <option value="">Choose a persona…</option>
          {emps && emps.map((x) => <option value={x.id} key={x.id}>{x.full_name} — {x.department}</option>)}
        </select>
        <input style={{ minWidth: 260, flex: 1 }} value={obj} onChange={(x) => setObj(x.target.value)} placeholder="Training objective" />
        <select value={diff} onChange={(x) => setDiff(x.target.value)}>
          <option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option>
        </select>
        <select value={lang} onChange={(x) => setLang(x.target.value)} title="Output language">
          <option value="">Auto (persona)</option><option value="az">Azərbaycanca</option><option value="en">English</option><option value="ru">Русский</option>
        </select>
        <button disabled={!emp || busy} onClick={gen}>{busy ? 'Generating…' : 'Generate message'}</button>
      </div>
      <div className="stack" style={{ marginTop: 4 }}>
        {scen === null ? <Load /> : scen.length === 0
          ? <Empty>No simulations yet. Pick a persona above and generate the first message.</Empty>
          : scen.map((s) => <ScenarioCard key={s.id} s={s} onChange={refresh} />)}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ analytics */
function Analytics() {
  const [d, e] = useLoad('/analytics');
  if (e) return <Err e={e} />;
  if (!d) return <Load />;
  return (
    <>
      <Head eyebrow="Campaign outcomes" title="Analytics" sub="Aggregated across every launched simulation." />
      <section className="grid4">
        <Metric label="Targets" value={d.targets} />
        <Metric label="Delivery" value={d.delivery_rate} unit="%" fill={d.delivery_rate} />
        <Metric label="Open rate" value={d.open_rate} unit="%" fill={d.open_rate} />
        <Metric label="Avg response" value={d.average_response_time_seconds} unit="s" />
      </section>
      <section className="grid4" style={{ marginTop: 16 }}>
        <Metric label="Click rate" value={d.click_rate} unit="%" fill={d.click_rate} />
        <Metric label="Submission" value={d.submission_rate} unit="%" fill={d.submission_rate} />
        <Metric label="Reported" value={d.reporting_rate} unit="%" fill={d.reporting_rate} />
        <Metric label="Campaigns" value={d.campaigns} />
      </section>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Average risk by department</h3>
        {d.by_department && d.by_department.length ? (
          <table>
            <thead><tr><th>Department</th><th>Employees</th><th style={{ width: '45%' }}>Average risk</th></tr></thead>
            <tbody>
              {d.by_department.map((row) => (
                <tr key={row.department}>
                  <td style={{ fontWeight: 600 }}>{row.department}</td>
                  <td className="mono">{row.employees}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span className="ftrack" style={{ flex: 1, height: 8, borderRadius: 5, background: 'var(--surface-2)', overflow: 'hidden' }}>
                        <i style={{ display: 'block', height: '100%', width: row.average_risk + '%', background: riskColor(row.average_risk) }} />
                      </span>
                      <span className="mono" style={{ width: 42, textAlign: 'right' }}>{row.average_risk}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty>No department data yet.</Empty>}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ training */
function Recs() {
  const [d, e] = useLoad('/recommendations');
  if (e) return <Err e={e} />;
  if (!d) return <Load />;
  return (
    <>
      <Head eyebrow="Corrective guidance" title="Training recommendations" sub="Derived from how each persona responded to simulations." />
      {d.length === 0 ? <Empty>No recommendations yet — run a simulation first.</Empty> : (
        <div className="stack">
          {d.map((x, i) => (
            <div className="card row" key={i} style={{ alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontWeight: 600 }}>{x.employee}</div>
                <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>{titleCase(x.topic)} — {x.recommendation}</div>
              </div>
              <Badge kind={x.priority}>{x.priority}</Badge>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ system */
function Status() {
  const [h, e] = useLoad('/health');
  if (e) return <Err e={e} />;
  if (!h) return <Load />;
  const labels = { llm: 'Content generation', campaign: 'Campaign engine', email: 'Email delivery' };
  return (
    <>
      <Head eyebrow="Integration status" title="System" sub="Mock mode exercises the same service interfaces as real integrations." />
      <div className="card">
        <div className="row" style={{ marginBottom: 18 }}>
          <div><div className="eyebrow">Service</div><div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 600 }}>{h.app}</div></div>
          <Badge kind={h.status === 'ok' ? 'low' : 'critical'}>{h.status === 'ok' ? 'operational' : h.status}</Badge>
        </div>
        <div className="chips">
          {Object.entries(h.mode).map(([k, v]) => {
            const mock = v === 'mock';
            return (
              <div className="provider" key={k}>
                <div className="k">{labels[k] || k}</div>
                <div className="v">{v}</div>
                <div className={'state ' + (mock ? 'mock' : 'live')}><span className="dot" />{mock ? 'mock (offline)' : 'live provider'}</div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ victim landing */
function Sim() {
  const { sid } = useParams();
  const [d, e] = useLoad('/simulation/' + sid);
  const toast = useToast();
  const [done, setDone] = useState('');
  const [opened, setOpened] = useState(false);
  const ev = async (type, pw) => {
    try {
      await api(`/simulation/${sid}/event`, { method: 'POST', body: JSON.stringify({ session_id: sid, event_type: type, password: pw }) });
      setDone(type);
      const notes = {
        link_clicked: 'Link click recorded — in a real attack this is where you land on a fake page.',
        form_viewed: 'Form view recorded.',
        credential_simulation_submitted: 'Recorded. Any value you typed was discarded immediately — never stored.',
        simulation_reported: 'Nicely done — reporting is exactly the right move.',
      };
      toast(notes[type] || 'Recorded.', type === 'simulation_reported' ? 'ok' : 'info');
    } catch (x) { toast(x.message, 'err'); }
  };
  if (e) return <div className="landing"><Err e={e} /></div>;
  if (!d) return <div className="landing"><Load /></div>;
  const recipientEmail = (d.recipient.match(/<(.+)>/) || [])[1] || d.recipient;
  return (
    <div className="landing">
      <div className="banner">⚠ AUTHORIZED SECURITY-AWARENESS SIMULATION — this is a training exercise. Never enter a real password.</div>

      <div className="mailcard">
        <div className="mailhead">
          <div className="mrow"><span>From</span><b>{d.sender}</b></div>
          <div className="mrow"><span>To</span><span className="muted">{d.recipient}</span></div>
          <div className="mrow"><span>Subject</span><b>{d.subject}</b></div>
        </div>
        <div className="mailbody">
          <p>{d.email_body}</p>
          <button onClick={() => { setOpened(true); ev('link_clicked'); }}>Open secure portal →</button>
        </div>
      </div>

      <div className="card portal">
        <div className="eyebrow">corp-portal.example</div>
        <h3 style={{ marginTop: 6 }}>Sign in to continue</h3>
        <p className="muted" style={{ marginTop: 0 }}>You reached this page by following the link in the message above. In a real attack, this page would steal whatever you type.</p>
        <div className="editform">
          <label>Email</label>
          <input value={recipientEmail} readOnly />
          <label>Password — simulation value only, never a real one</label>
          <input id="pw" type="password" placeholder="Type a fake demo value" onFocus={() => !opened && ev('form_viewed')} />
        </div>
        <div className="actions">
          <button onClick={() => ev('credential_simulation_submitted', document.getElementById('pw').value)}>Sign in</button>
          <button className="ghost" onClick={() => ev('simulation_reported')}>This looks like phishing — report it</button>
        </div>
      </div>

      <div className="disclose">{d.landing_page_message}</div>
      {done && <p className="muted" style={{ textAlign: 'center' }}>Safe simulation complete — your “{done.replace(/_/g, ' ')}” response was recorded for awareness training. No credentials were stored.</p>}
    </div>
  );
}

/* ------------------------------------------------------------------ root */
function App() {
  return (
    <Routes>
      <Route path="/simulate/:sid" element={<Sim />} />
      <Route path="*" element={
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/employees" element={<Employees />} />
            <Route path="/employees/:id" element={<Employee />} />
            <Route path="/simulations" element={<Simulations />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/recommendations" element={<Recs />} />
            <Route path="/status" element={<Status />} />
          </Routes>
        </Layout>
      } />
    </Routes>
  );
}
createRoot(document.getElementById('root')).render(
  <ThemeProvider><ToastProvider><BrowserRouter><App /></BrowserRouter></ToastProvider></ThemeProvider>
);
