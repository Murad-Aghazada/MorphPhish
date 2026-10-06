import React, { useEffect, useRef, useState, useCallback, useContext, createContext } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, NavLink, useParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend, LabelList } from 'recharts';
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

/* ------------------------------------------------------------------ charts (Week 4)
   Every chart re-reads theme tokens on toggle (keyed by theme), ships a hover
   tooltip, and encodes identity with a legend + direct labels — never color
   alone. Palette: CVD-validated series tokens + the shared risk ramp. */
function useChartTokens() {
  const { theme } = useContext(ThemeCtx);           // re-read on theme change
  return { theme, grid: cssVar('--border'), muted: cssVar('--muted'), surface: cssVar('--surface'), ink: cssVar('--ink') };
}
const chartTip = (t) => ({ cursor: { fill: 'color-mix(in srgb, var(--iris) 8%, transparent)' },
  contentStyle: { background: t.surface, border: '1px solid ' + t.grid, borderRadius: 12, color: t.ink, fontSize: 13 },
  labelStyle: { color: t.muted } });

// Average risk (0–100) across a dimension — colored by the risk ramp.
function RiskByDimension({ data, height = 300 }) {
  const t = useChartTokens();
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 8, left: -12, bottom: 0 }} key={t.theme}>
        <XAxis dataKey="key" interval={0} tick={{ fill: t.muted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: t.grid }} angle={data.length > 6 ? -18 : 0} textAnchor={data.length > 6 ? 'end' : 'middle'} height={data.length > 6 ? 56 : 30} />
        <YAxis domain={[0, 100]} tick={{ fill: t.muted, fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip {...chartTip(t)} formatter={(v) => [v, 'avg risk']} />
        <Bar dataKey="average_risk" radius={[6, 6, 0, 0]} maxBarSize={54}>
          {data.map((d, i) => <Cell key={i} fill={riskColor(d.average_risk)} />)}
          <LabelList dataKey="average_risk" position="top" fill={t.muted} fontSize={11} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Engagement funnel: delivered → opened → clicked → submitted → reported.
// One measure across ordered stages → horizontal bars, single sequential hue.
const STAGE_LABEL = { delivered: 'Delivered', opened: 'Opened', clicked: 'Clicked', submitted: 'Submitted', reported: 'Reported' };
function FunnelChart({ data, height = 260 }) {
  const t = useChartTokens();
  const rows = data.map((d) => ({ ...d, name: STAGE_LABEL[d.stage] || d.stage }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart layout="vertical" data={rows} margin={{ top: 4, right: 44, left: 8, bottom: 0 }} key={t.theme}>
        <XAxis type="number" domain={[0, 100]} hide />
        <YAxis type="category" dataKey="name" width={78} tick={{ fill: t.muted, fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip {...chartTip(t)} formatter={(v, n, p) => [`${p.payload.count} (${v}%)`, 'reached']} />
        <Bar dataKey="rate" fill="var(--series-1)" radius={[0, 5, 5, 0]} maxBarSize={30} background={{ fill: 'var(--surface-2)', radius: 5 }}>
          <LabelList dataKey="count" position="right" fill={t.ink} fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Risk-level distribution across the workforce — ordered severity, status colors.
const LEVEL_COLOR = { critical: 'var(--risk-critical)', high: 'var(--risk-high)', medium: 'var(--risk-medium)', low: 'var(--risk-low)' };
function RiskDistribution({ data, height = 260 }) {
  const t = useChartTokens();
  const rows = data.map((d) => ({ ...d, name: d.level[0].toUpperCase() + d.level.slice(1) }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart layout="vertical" data={rows} margin={{ top: 4, right: 36, left: 8, bottom: 0 }} key={t.theme}>
        <XAxis type="number" allowDecimals={false} hide />
        <YAxis type="category" dataKey="name" width={70} tick={{ fill: t.muted, fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip {...chartTip(t)} formatter={(v) => [v, 'employees']} />
        <Bar dataKey="count" radius={[0, 5, 5, 0]} maxBarSize={30}>
          {rows.map((d, i) => <Cell key={i} fill={LEVEL_COLOR[d.level]} />)}
          <LabelList dataKey="count" position="right" fill={t.ink} fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Engagement rates (click / submission / reporting) across a dimension.
// Three categorical series → grouped bars, legend + tooltip (identity never color-alone).
const ENGAGE = [['click_rate', 'Clicked', 'var(--series-1)'], ['submission_rate', 'Submitted', 'var(--series-2)'], ['reporting_rate', 'Reported', 'var(--series-3)']];
function EngagementByDimension({ data, height = 320 }) {
  const t = useChartTokens();
  const rows = data.filter((d) => d.delivered > 0);
  if (!rows.length) return <Empty>No delivered simulations in this cut yet.</Empty>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} key={t.theme} barGap={2} barCategoryGap="22%">
        <XAxis dataKey="key" interval={0} tick={{ fill: t.muted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: t.grid }} angle={rows.length > 5 ? -18 : 0} textAnchor={rows.length > 5 ? 'end' : 'middle'} height={rows.length > 5 ? 56 : 30} />
        <YAxis domain={[0, 100]} unit="%" tick={{ fill: t.muted, fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip {...chartTip(t)} formatter={(v, n) => [`${v}%`, n]} />
        <Legend wrapperStyle={{ fontSize: 12, color: t.muted }} iconType="circle" iconSize={9} />
        {ENGAGE.map(([k, name, color]) => (
          <Bar key={k} dataKey={k} name={name} fill={color} radius={[4, 4, 0, 0]} maxBarSize={26} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ dashboard */
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
      <section className="grid2" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Engagement funnel</h3><Badge kind="iris">% of delivered</Badge></div>
          {a.funnel && a.delivered > 0 ? <FunnelChart data={a.funnel} /> : <Empty>Launch a simulation to populate the funnel.</Empty>}
        </div>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Workforce risk distribution</h3><Badge kind="iris">employees</Badge></div>
          {a.risk_distribution && a.risk_distribution.some((r) => r.count) ? <RiskDistribution data={a.risk_distribution} /> : <Empty>No risk profiles yet.</Empty>}
        </div>
      </section>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Average risk by department</h3><Badge kind="iris">0–100 scale</Badge></div>
        {a.by_department && a.by_department.length ? <RiskByDimension data={a.by_department} /> : <Empty>No department data yet.</Empty>}
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
  const [result, setResult] = useState(null);
  const editable = EDITABLE.has(s.status);
  const loadResult = async () => { try { setResult(await api(`/scenarios/${s.id}/result`)); } catch { /* ignore */ } };
  useEffect(() => { if (s.status === 'ACTIVE') loadResult(); }, [s.status, s.id]); // show outcome once launched
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
      {s.status === 'ACTIVE' && result && result.targets && result.targets.length > 0 && (
        <SimResult target={result.targets[0]} onRefresh={loadResult} />
      )}
    </div>
  );
}
// Outcome of a launched simulation, shown on the Simulations tab.
const STAGES = [['opened', 'Opened', 'medium'], ['clicked', 'Clicked', 'high'], ['submitted', 'Submitted', 'critical'], ['reported', 'Reported', 'low']];
function simHeadline(t) {
  if (t.reported) return { text: 'Reported — did the right thing', kind: 'low' };
  if (t.submitted) return { text: 'Entered credentials on the fake page', kind: 'critical' };
  if (t.clicked) return { text: 'Clicked the link', kind: 'high' };
  if (t.opened) return { text: 'Opened the email', kind: 'medium' };
  return { text: 'Delivered — no interaction yet', kind: '' };
}
function SimResult({ target, onRefresh }) {
  const h = simHeadline(target);
  return (
    <div className="simresult">
      <div className="row" style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span className="mono" style={{ fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--muted)' }}>Result</span>
          <Badge kind={h.kind || 'iris'}>{h.text}</Badge>
        </div>
        <button className="secondary" onClick={onRefresh}>Refresh</button>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {STAGES.map(([key, label, kind]) => (
          <span key={key} className={'stagechip' + (target[key] ? ' on ' + kind : '')}>{target[key] ? '✓ ' : ''}{label}</span>
        ))}
      </div>
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
// Accessible table view of a dimension's metrics (also the relief/colorblind
// fallback for the grouped bar chart — identity is never color-alone).
function DimensionTable({ data, label }) {
  return (
    <table>
      <thead><tr><th>{label}</th><th>Staff</th><th>Avg risk</th><th>Sent</th><th>Click</th><th>Submit</th><th>Report</th><th>Resp (s)</th></tr></thead>
      <tbody>
        {data.map((r) => (
          <tr key={r.key}>
            <td style={{ fontWeight: 600 }}>{r.key}</td>
            <td className="mono">{r.employees}</td>
            <td><span className="riskpill" style={{ color: riskColor(r.average_risk), borderColor: 'color-mix(in srgb, ' + riskColor(r.average_risk) + ' 40%, transparent)' }}>{r.average_risk}</span></td>
            <td className="mono">{r.delivered}</td>
            <td className="mono">{r.click_rate}%</td>
            <td className="mono">{r.submission_rate}%</td>
            <td className="mono">{r.reporting_rate}%</td>
            <td className="mono">{r.average_response_time_seconds || '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
function Analytics() {
  const [d, e] = useLoad('/analytics');
  if (e) return <Err e={e} />;
  if (!d) return <Load />;
  const hasData = d.delivered > 0;
  return (
    <>
      <Head eyebrow="Campaign outcomes" title="Analytics" sub="Role- and department-level human-risk map across every launched simulation." />
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
      <section className="grid2" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Engagement funnel</h3><Badge kind="iris">% of delivered</Badge></div>
          {hasData ? <FunnelChart data={d.funnel} /> : <Empty>Launch a simulation to populate the funnel.</Empty>}
        </div>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Workforce risk distribution</h3><Badge kind="iris">employees</Badge></div>
          {d.risk_distribution && d.risk_distribution.some((r) => r.count) ? <RiskDistribution data={d.risk_distribution} /> : <Empty>No risk profiles yet.</Empty>}
        </div>
      </section>
      <section className="grid2" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Average risk by department</h3>
          {d.by_department && d.by_department.length ? <RiskByDimension data={d.by_department} /> : <Empty>No department data yet.</Empty>}
        </div>
        <div className="card">
          <h3>Average risk by role</h3>
          {d.by_role && d.by_role.length ? <RiskByDimension data={d.by_role} /> : <Empty>No role data yet.</Empty>}
        </div>
      </section>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Engagement by department</h3><Badge kind="iris">% of delivered</Badge></div>
        {d.by_department && d.by_department.length ? <EngagementByDimension data={d.by_department} /> : <Empty>No department data yet.</Empty>}
        {d.by_department && d.by_department.length > 0 && <div style={{ marginTop: 14 }}><DimensionTable data={d.by_department} label="Department" /></div>}
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Engagement by role</h3>
        {d.by_role && d.by_role.length ? <DimensionTable data={d.by_role} label="Role" /> : <Empty>No role data yet.</Empty>}
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

/* ------------------------------------------------------------------ victim landing
   A realistic corporate-portal sign-in page. No upfront disclosure — following
   the email link is itself the click (recorded on mount); the teachable-moment
   debrief appears only AFTER the person submits or reports. The password is
   discarded by the backend and never leaves the browser as anything stored. */
const RED_FLAGS = [
  'Unexpected urgency or a same-day deadline pushing you to act fast',
  'A button or link asking you to “sign in” or “verify” your account',
  'A sender or team you did not expect — even if the name looks familiar',
  'Any page asking for your password after you followed a link in an email',
];
function Sim() {
  const { sid } = useParams();
  const [d, e] = useLoad('/simulation/' + sid);
  const [phase, setPhase] = useState('login');   // 'login' | 'debrief'
  const [outcome, setOutcome] = useState(null);   // 'submitted' | 'reported'
  const [pw, setPw] = useState('');
  const landed = useRef(false);
  const viewed = useRef(false);
  const ev = (type, password) =>
    api(`/simulation/${sid}/event`, { method: 'POST', body: JSON.stringify({ session_id: sid, event_type: type, password }) }).catch(() => {});
  useEffect(() => { if (d && !landed.current) { landed.current = true; ev('link_clicked'); } }, [d]);
  const submit = () => { ev('credential_simulation_submitted', pw); setOutcome('submitted'); setPhase('debrief'); };
  const report = () => { ev('simulation_reported'); setOutcome('reported'); setPhase('debrief'); };
  const restart = () => { viewed.current = false; setPw(''); setOutcome(null); setPhase('login'); };

  if (e) return <div className="landing"><Err e={e} /></div>;
  if (!d) return <div className="landing"><Load /></div>;
  const recipientEmail = (d.recipient.match(/<(.+)>/) || [])[1] || d.recipient;
  const brand = (d.sender || '').split(' <')[0] || 'Account Services';

  if (phase === 'debrief') {
    const reported = outcome === 'reported';
    return (
      <div className="loginwrap">
        <div className="logincard debrief">
          <div className={'debrief-tag ' + (reported ? 'good' : 'warn')}>
            {reported ? '✓ You reported it — exactly right' : '⚠ This was a simulation'}
          </div>
          <h2>Authorized security-awareness simulation</h2>
          <p className="disclose-text">{d.landing_page_message}</p>
          {!reported && <p className="muted">You submitted on a simulated sign-in page. In a real attack this is the moment credentials are stolen — but here nothing you typed was stored, hashed, logged, or sent anywhere.</p>}
          <div className="flags">
            <div className="flags-title">What to watch for next time</div>
            <ul>{RED_FLAGS.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
          <p className="muted small">This was part of an authorized, non-punitive training exercise using synthetic data. Questions go to your security team.</p>
          <button className="loginbtn" style={{ marginTop: 18 }} onClick={restart}>Run the simulation again</button>
        </div>
      </div>
    );
  }
  return (
    <div className="loginwrap">
      <div className="logincard">
        <div className="loginbrand">{brand}</div>
        <h2>Sign in</h2>
        <p className="muted">Sign in to continue to your account.</p>
        <div className="editform">
          <label>Email</label>
          <input value={recipientEmail} readOnly />
          <label>Password</label>
          <input type="password" value={pw} placeholder="Enter your password"
            onFocus={() => { if (!viewed.current) { viewed.current = true; ev('form_viewed'); } }}
            onChange={(ev2) => setPw(ev2.target.value)}
            onKeyDown={(ev2) => ev2.key === 'Enter' && submit()} />
        </div>
        <button className="loginbtn" onClick={submit}>Sign in</button>
        <button className="reportlink" onClick={report}>Report this message as phishing</button>
      </div>
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
