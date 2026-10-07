import React, { useEffect, useRef, useState, useCallback, useContext, createContext } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, NavLink, useParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend, LabelList } from 'recharts';
import { api, setToken, getToken } from './api';
import './styles.css';

/* ------------------------------------------------------------------ auth */
const AuthCtx = createContext({ authed: false, login: async () => {}, logout: () => {} });
const useAuth = () => useContext(AuthCtx);
function AuthProvider({ children }) {
  const [authed, setAuthed] = useState(() => !!getToken());
  const [ready, setReady] = useState(() => !getToken()); // if no token, nothing to validate
  useEffect(() => {
    const onUnauth = () => setAuthed(false);
    window.addEventListener('mp-unauthorized', onUnauth);
    return () => window.removeEventListener('mp-unauthorized', onUnauth);
  }, []);
  useEffect(() => {
    if (!getToken()) return;
    api('/auth/me').then(() => setAuthed(true)).catch(() => { setToken(''); setAuthed(false); }).finally(() => setReady(true));
  }, []);
  const login = useCallback(async (u, p) => {
    const r = await api('/auth/login', { method: 'POST', body: JSON.stringify({ username: u, password: p }) });
    setToken(r.access_token); setAuthed(true); setReady(true);
  }, []);
  const logout = useCallback(() => { setToken(''); setAuthed(false); }, []);
  return <AuthCtx.Provider value={{ authed, ready, login, logout }}>{children}</AuthCtx.Provider>;
}
function Login() {
  const { login } = useAuth();
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const submit = async (e) => {
    if (e) e.preventDefault();
    setBusy(true); setErr('');
    try { await login(u.trim(), p); } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <div className="loginpage">
      <div className="loginpanel">
        <aside className="login-aside">
          <div className="login-aside-top">
            <div className="login-logo"><Glyph /><span>MorphPhish</span></div>
            <p className="login-aside-tag">Role-aware phishing-awareness simulation for security teams.</p>
          </div>
          <ul className="login-points">
            <li>Generate contextual, approval-gated simulations</li>
            <li>Track the open → click → report funnel per team</li>
            <li>Turn outcomes into an explainable human-risk map</li>
          </ul>
          <div className="login-aside-foot">Authorized security testing · synthetic data only</div>
        </aside>

        <main className="login-main">
          <form className="login-form" onSubmit={submit}>
            <div className="login-logo compact"><Glyph /><span>MorphPhish</span></div>
            <h1 className="login-title">Welcome back</h1>
            <p className="login-sub">Sign in to the admin console.</p>

            <label htmlFor="lg-user">Username</label>
            <div className="login-field">
              <input id="lg-user" autoFocus value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" placeholder="Your username" />
            </div>

            <label htmlFor="lg-pass">Password</label>
            <div className="login-field">
              <input id="lg-pass" type={show ? 'text' : 'password'} value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" placeholder="Your password" />
              <button type="button" className="login-eye" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'} tabIndex={-1}>
                {show ? 'Hide' : 'Show'}
              </button>
            </div>

            {err && <p className="loginerr" role="alert">{err}</p>}

            <button className="loginbtn" disabled={busy || !u || !p} type="submit">{busy ? 'Signing in…' : 'Sign in'}</button>

            <p className="login-secure">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="4" y="11" width="16" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" />
              </svg>
              Authorized use only. Activity is logged and sessions expire automatically.
            </p>
          </form>
        </main>
      </div>
    </div>
  );
}

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
const STALE_DAYS = 7;
const fmtDate = (iso) => { if (!iso) return ''; const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }); };
const daysSince = (iso) => { if (!iso) return null; return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000); };
const simTime = (s) => Date.parse((s.outcome && s.outcome.launched_at) || s.created_at) || 0;
const sortByTime = (list, dir) => [...list].sort((a, b) => dir === 'asc' ? simTime(a) - simTime(b) : simTime(b) - simTime(a));
const SortToggle = ({ dir, onToggle }) => <button className="secondary" onClick={onToggle} title="Sort by date">{dir === 'desc' ? 'Newest first ↓' : 'Oldest first ↑'}</button>;
const ARCHIVED_STATUSES = new Set(['COMPLETED', 'CLOSED', 'REJECTED']);
// A terminal response completes a run; legacy rows may still read ACTIVE, so treat
// a completed ACTIVE scenario as COMPLETED for the badge and the tab split.
const effStatus = (s) => (s.completed && s.status === 'ACTIVE') ? 'COMPLETED' : s.status;
const isArchived = (s) => s.completed || ARCHIVED_STATUSES.has(s.status);
const isLaunched = (s) => ['ACTIVE', 'COMPLETED', 'CLOSED'].includes(s.status);

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
  ['/archive', 'Archive'], ['/analytics', 'Analytics'], ['/recommendations', 'Training'],
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
  const { logout } = useAuth();
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
          <button className="logoutbtn" onClick={logout}>Sign out</button>
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
// Horizontal mode keeps long labels (e.g. role titles) readable instead of overflowing.
const truncLabel = (v) => (v && v.length > 24 ? v.slice(0, 23) + '…' : v);
function RiskByDimension({ data, height = 300, horizontal = false }) {
  const t = useChartTokens();
  if (horizontal) {
    const h = Math.max(height, data.length * 34 + 24);
    return (
      <ResponsiveContainer width="100%" height={h}>
        <BarChart layout="vertical" data={data} margin={{ top: 4, right: 40, left: 8, bottom: 0 }} key={t.theme}>
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis type="category" dataKey="key" width={150} interval={0} tick={{ fill: t.muted, fontSize: 12 }} tickLine={false} axisLine={false} tickFormatter={truncLabel} />
          <Tooltip {...chartTip(t)} formatter={(v) => [v, 'avg risk']} />
          <Bar dataKey="average_risk" radius={[0, 5, 5, 0]} maxBarSize={24}>
            {data.map((d, i) => <Cell key={i} fill={riskColor(d.average_risk)} />)}
            <LabelList dataKey="average_risk" position="right" fill={t.muted} fontSize={11} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 8, left: -12, bottom: 0 }} key={t.theme}>
        <XAxis dataKey="key" interval={0} tick={{ fill: t.muted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: t.grid }} angle={data.length > 6 ? -18 : 0} textAnchor={data.length > 6 ? 'end' : 'middle'} height={data.length > 6 ? 56 : 30} tickFormatter={truncLabel} />
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
        <Metric label="Click rate" value={a.click_rate} unit="%" fill={a.click_rate} />
        <Metric label="Submission rate" value={a.submission_rate} unit="%" fill={a.submission_rate} />
        <Metric label="Report rate" value={a.reporting_rate} unit="%" fill={a.reporting_rate} />
        <Metric label="High-risk staff" value={`${a.high_risk_employees ?? 0}/${a.employees_total ?? 0}`} />
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
const EMP_SORTS = [['risk-desc', 'Risk high→low'], ['risk-asc', 'Risk low→high'], ['name-asc', 'Name A→Z'], ['dept-asc', 'Department']];
function Employees() {
  const [d, e, setD] = useLoad('/employees');
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState('');
  const [dept, setDept] = useState('all');
  const [level, setLevel] = useState('all');
  const [sort, setSort] = useState('risk-desc');
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
  const depts = d ? Array.from(new Set(d.map((x) => x.department).filter(Boolean))).sort() : [];
  const filtered = d ? d
    .filter((x) =>
      (dept === 'all' || x.department === dept) &&
      (level === 'all' || x.risk_level === level) &&
      (!q || x.full_name.toLowerCase().includes(q.toLowerCase()) || x.role.toLowerCase().includes(q.toLowerCase())))
    .sort((a, b) => {
      const sa = a.risk_score ?? -1, sb = b.risk_score ?? -1;
      if (sort === 'risk-desc') return sb - sa;
      if (sort === 'risk-asc') return sa - sb;
      if (sort === 'name-asc') return a.full_name.localeCompare(b.full_name);
      return a.department.localeCompare(b.department) || a.full_name.localeCompare(b.full_name);
    }) : [];
  return (
    <>
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <Head eyebrow="Personas from the HR data layer" title="Employees" sub="Role, department, and language drive each persona's risk profile." />
        <button className="secondary" onClick={sync} disabled={busy}>{busy ? 'Syncing…' : 'Sync from HR'}</button>
      </div>
      {!d ? <Load /> : (
        <>
          <div className="card form" style={{ flexWrap: 'wrap' }}>
            <input style={{ minWidth: 200, flex: 1 }} value={q} onChange={(x) => setQ(x.target.value)} placeholder="Search name or role…" />
            <select value={dept} onChange={(x) => setDept(x.target.value)} title="Department">
              <option value="all">All departments</option>
              {depts.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
            <select value={level} onChange={(x) => setLevel(x.target.value)} title="Risk level">
              <option value="all">All risk levels</option>
              <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
            </select>
            <select value={sort} onChange={(x) => setSort(x.target.value)} title="Sort by">
              {EMP_SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <p className="muted" style={{ fontSize: 13, margin: '2px 2px 8px' }}>{filtered.length} of {d.length} personas</p>
          <div className="card" style={{ padding: 8 }}>
            {filtered.length === 0 ? <Empty>No personas match these filters.</Empty> : (
              <table>
                <thead><tr><th>Name</th><th>Department</th><th>Role</th><th>Lang</th><th>Risk</th><th>Source</th><th /></tr></thead>
                <tbody>
                  {filtered.map((x) => (
                    <tr key={x.id}>
                      <td style={{ fontWeight: 600 }}>{x.full_name}</td>
                      <td>{x.department}</td>
                      <td className="muted">{x.role}</td>
                      <td className="mono">{x.preferred_language}</td>
                      <td>{x.risk_score != null
                        ? <span className="riskpill" style={{ color: riskColor(x.risk_score), borderColor: 'color-mix(in srgb, ' + riskColor(x.risk_score) + ' 40%, transparent)' }} title={x.risk_level}>{Math.round(x.risk_score)}</span>
                        : <span className="muted">—</span>}</td>
                      <td><span className="badge" title={x.external_id || ''}>{x.source}</span></td>
                      <td style={{ textAlign: 'right' }}><NavLink to={`/employees/${x.id}`}>View →</NavLink></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
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
  const [result, setResult] = useState(null);
  const editable = EDITABLE.has(s.status);
  const loadResult = async () => { try { setResult(await api(`/scenarios/${s.id}/result`)); } catch { /* ignore */ } };
  useEffect(() => { if (isLaunched(s)) loadResult(); }, [s.status, s.id]); // show outcome once launched
  const run = async (fn, ok) => { try { const r = await fn(); if (ok) toast(ok, 'ok'); onChange(); return r; } catch (x) { toast(x.message, 'err'); } };
  const save = () => run(async () => { await api(`/scenarios/${s.id}`, { method: 'PATCH', body: JSON.stringify(f) }); setEdit(false); }, 'Message updated.');
  const act = (path, ok) => run(() => api(`/scenarios/${s.id}/${path}`, { method: 'POST' }), ok);
  // Regenerate updates THIS scenario in place (no new card).
  const regen = () => run(() => api(`/scenarios/${s.id}/regenerate`, { method: 'POST' }), 'Scenario regenerated.');
  const close = () => run(() => api(`/scenarios/${s.id}/close`, { method: 'POST' }), 'Simulation closed — no response.');
  const awaiting = s.status === 'ACTIVE' && !s.completed;       // launched, no terminal response yet
  const idleDays = awaiting ? daysSince((s.outcome && (s.outcome.last_event_at || s.outcome.launched_at)) || s.created_at) : null;
  const stale = idleDays != null && idleDays >= STALE_DAYS;
  const dateLabel = (s.outcome && s.outcome.launched_at) ? 'Launched ' + fmtDate(s.outcome.launched_at) : 'Generated ' + fmtDate(s.created_at);
  const doLaunch = async () => {
    const r = await run(() => api(`/scenarios/${s.id}/launch`, { method: 'POST', body: JSON.stringify({}) }), 'Simulation launched.');
    if (r) setLaunch(r);
  };
  return (
    <div className="card scen">
      <div className="row"><h3 style={{ margin: 0, maxWidth: '70%' }}>{s.subject}</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {s.quality_score != null && <Badge kind={s.quality_score >= 80 ? 'low' : s.quality_score >= 50 ? 'medium' : 'high'} title="Automated quality score">Q {Math.round(s.quality_score)}</Badge>}
          <Badge kind={'status-' + effStatus(s).toLowerCase()}>{effStatus(s).replace('_', ' ')}</Badge>
        </div>
      </div>
      <div className="cardmeta">
        <span>{dateLabel}</span>
        {awaiting && <span className={'awaiting' + (stale ? ' stale' : '')}>{stale ? '⚠ No response' : 'Awaiting response'}{idleDays != null ? ` · ${idleDays}d` : ''}</span>}
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
          {s.status === 'APPROVED' && <button onClick={doLaunch}>Launch simulation</button>}
          {awaiting && <button className="ghost" onClick={close} title="No terminal response — move to Archive">Close as no-response</button>}
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
      {isLaunched(s) && result && result.targets && result.targets.length > 0 && (
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
  const [sort, setSort] = useState('desc');
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
      {scen === null ? <Load /> : (() => {
        // Active = still in the pipeline, or launched but not completed/closed.
        const active = sortByTime(scen.filter((s) => !isArchived(s)), sort);
        if (active.length === 0) return <div className="stack" style={{ marginTop: 4 }}><Empty>No active simulations. Pick a persona above and generate a message — finished ones move to <b>Archive</b>.</Empty></div>;
        return (
          <>
            <div className="row" style={{ margin: '4px 2px 0' }}>
              <span className="muted" style={{ fontSize: 13 }}>{active.length} active</span>
              <SortToggle dir={sort} onToggle={() => setSort((d) => d === 'desc' ? 'asc' : 'desc')} />
            </div>
            <div className="stack" style={{ marginTop: 4 }}>
              {active.map((s) => <ScenarioCard key={s.id} s={s} onChange={refresh} />)}
            </div>
          </>
        );
      })()}
    </>
  );
}

/* ------------------------------------------------------------------ archive */
// Classify an archived scenario into one outcome bucket (worst reached stage).
function outcomeBucket(s) {
  if (s.status === 'REJECTED') return 'rejected';
  const o = s.outcome || {};
  if (o.reported) return 'reported';
  if (o.submitted) return 'submitted';
  if (o.clicked) return 'clicked';
  if (o.opened) return 'opened';
  return 'none';
}
const OUTCOME_OPTS = [['all', 'All outcomes'], ['reported', 'Reported'], ['submitted', 'Submitted'], ['clicked', 'Clicked'], ['opened', 'Opened only'], ['none', 'No interaction'], ['rejected', 'Rejected']];
function Archive() {
  const [scen, e, setScen] = useLoad('/scenarios');
  const [q, setQ] = useState('');
  const [outcome, setOutcome] = useState('all');
  const [lang, setLang] = useState('all');
  const [diff, setDiff] = useState('all');
  const [dept, setDept] = useState('all');
  const [sort, setSort] = useState('desc');
  const refresh = async () => setScen(await api('/scenarios'));
  if (e) return <Err e={e} />;
  if (!scen) return <Load />;
  // Archived = completed (submitted/reported), closed as no-response, or rejected.
  const archived = scen.filter(isArchived);
  const depts = Array.from(new Set(archived.map((s) => s.department).filter(Boolean))).sort();
  const filtered = sortByTime(archived.filter((s) =>
    (outcome === 'all' || outcomeBucket(s) === outcome) &&
    (lang === 'all' || s.language === lang) &&
    (diff === 'all' || s.difficulty === diff) &&
    (dept === 'all' || s.department === dept) &&
    (!q || (s.outcome && (s.outcome.recipient_name || '').toLowerCase().includes(q.toLowerCase())))  // search by recipient name only
  ), sort);
  return (
    <>
      <Head eyebrow="Finished simulations" title="Archive" sub="Completed runs, no-response closures, and rejected drafts." />
      <div className="card form" style={{ flexWrap: 'wrap' }}>
        <input style={{ minWidth: 200, flex: 1 }} value={q} onChange={(x) => setQ(x.target.value)} placeholder="Search by recipient name…" />
        <select value={outcome} onChange={(x) => setOutcome(x.target.value)} title="Outcome">
          {OUTCOME_OPTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select value={dept} onChange={(x) => setDept(x.target.value)} title="Department">
          <option value="all">All departments</option>
          {depts.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select value={lang} onChange={(x) => setLang(x.target.value)} title="Language">
          <option value="all">All languages</option><option value="az">AZ</option><option value="en">EN</option><option value="ru">RU</option>
        </select>
        <select value={diff} onChange={(x) => setDiff(x.target.value)} title="Difficulty">
          <option value="all">All levels</option><option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option>
        </select>
        <SortToggle dir={sort} onToggle={() => setSort((d) => d === 'desc' ? 'asc' : 'desc')} />
      </div>
      <p className="muted" style={{ fontSize: 13, margin: '2px 2px 8px' }}>{filtered.length} of {archived.length} archived</p>
      <div className="stack" style={{ marginTop: 4 }}>
        {archived.length === 0 ? <Empty>Nothing archived yet. A simulation moves here once the recipient submits or reports, when it is closed as no-response, or when a draft is rejected.</Empty>
          : filtered.length === 0 ? <Empty>No archived simulations match these filters.</Empty>
            : filtered.map((s) => <ScenarioCard key={s.id} s={s} onChange={refresh} />)}
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
        <Metric label="Simulations sent" value={d.targets} />
        <Metric label="Click rate" value={d.click_rate} unit="%" fill={d.click_rate} />
        <Metric label="Submission rate" value={d.submission_rate} unit="%" fill={d.submission_rate} />
        <Metric label="Report rate" value={d.reporting_rate} unit="%" fill={d.reporting_rate} />
      </section>
      <section className="grid4" style={{ marginTop: 16 }}>
        <Metric label="Opened rate" value={d.open_rate} unit="%" fill={d.open_rate} />
        <Metric label="Avg response" value={d.average_response_time_seconds} unit="s" />
        <Metric label="People targeted" value={`${d.people_targeted ?? 0}/${d.employees_total ?? 0}`} />
        <Metric label="High-risk staff" value={`${d.high_risk_employees ?? 0}/${d.employees_total ?? 0}`} />
      </section>
      <section className="grid2" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Compromise funnel</h3><Badge kind="iris">% of delivered</Badge></div>
          {hasData ? <FunnelChart data={d.funnel} /> : <Empty>Launch a simulation to populate the funnel.</Empty>}
        </div>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Workforce risk distribution</h3><Badge kind="iris">employees</Badge></div>
          {d.risk_distribution && d.risk_distribution.some((r) => r.count) ? <RiskDistribution data={d.risk_distribution} /> : <Empty>No risk profiles yet.</Empty>}
        </div>
      </section>
      <section className="grid2" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Average risk by department</h3><Badge kind="iris">0–100</Badge></div>
          {d.by_department && d.by_department.length ? <RiskByDimension data={d.by_department} /> : <Empty>No department data yet.</Empty>}
        </div>
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Average risk by role</h3><Badge kind="iris">0–100</Badge></div>
          {d.by_role && d.by_role.length ? <RiskByDimension data={d.by_role} horizontal /> : <Empty>No role data yet.</Empty>}
        </div>
      </section>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="row" style={{ marginBottom: 8 }}><h3 style={{ margin: 0 }}>Engagement by department</h3><Badge kind="iris">% of delivered</Badge></div>
        {d.by_department && d.by_department.length ? <EngagementByDimension data={d.by_department} /> : <Empty>No department data yet.</Empty>}
        {d.by_department && d.by_department.length > 0 && <div style={{ marginTop: 14 }}><DimensionTable data={d.by_department} label="Department" /></div>}
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginTop: 0 }}>Engagement by role</h3>
        {d.by_role && d.by_role.length ? <DimensionTable data={d.by_role} label="Role" /> : <Empty>No role data yet.</Empty>}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ training */
const trainStatusChip = (s) =>
  s === 'completed' ? <span className="stagechip on low">✓ Completed</span>
    : s === 'assigned' ? <span className="stagechip on medium">Assigned</span>
      : <span className="stagechip">Not assigned</span>;
function TrainingCard({ g, onAssign, onComplete, onRemove }) {
  return (
    <div className="card">
      <div className="row" style={{ alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {g.risk_score != null && <span className="riskpill" style={{ color: riskColor(g.risk_score), borderColor: 'color-mix(in srgb, ' + riskColor(g.risk_score) + ' 40%, transparent)' }} title={g.risk_level}>{Math.round(g.risk_score)}</span>}
          <div>
            <NavLink to={`/employees/${g.employee_id}`} style={{ fontWeight: 600 }}>{g.employee}</NavLink>
            <div className="muted" style={{ fontSize: 12.5 }}>{g.department} · {g.role}</div>
          </div>
        </div>
      </div>
      <div className="stack" style={{ marginTop: 12 }}>
        {g.items.map((i) => (
          <div className="trainrow" key={i.topic}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <Badge kind={i.priority}>{i.priority}</Badge><b>{titleCase(i.topic)}</b>{trainStatusChip(i.status)}
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>{i.recommendation}</div>
            </div>
            <div className="actions" style={{ flexShrink: 0 }}>
              {i.status === 'none' && <button onClick={() => onAssign(g.employee_id, i.topic)}>Assign</button>}
              {i.status === 'assigned' && <button onClick={() => onComplete(i.assignment_id)}>Mark complete</button>}
              {i.status !== 'none' && <button className="ghost" onClick={() => onRemove(i.assignment_id)}>Remove</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
function Training() {
  const [d, e, setD] = useLoad('/training');
  const toast = useToast();
  const [q, setQ] = useState('');
  const [dept, setDept] = useState('all');
  const [prio, setPrio] = useState('all');
  const [status, setStatus] = useState('all');
  const refresh = async () => setD(await api('/training'));
  const act = async (fn, ok) => { try { await fn(); toast(ok, 'ok'); await refresh(); } catch (x) { toast(x.message, 'err'); } };
  const onAssign = (employee_id, topic) => act(() => api('/training/assign', { method: 'POST', body: JSON.stringify({ employee_id, topic }) }), 'Training assigned.');
  const onComplete = (id) => act(() => api(`/training/${id}/complete`, { method: 'POST' }), 'Marked complete.');
  const onRemove = (id) => act(() => api(`/training/${id}`, { method: 'DELETE' }), 'Assignment removed.');
  if (e) return <Err e={e} />;
  if (!d) return <Load />;
  const depts = Array.from(new Set(d.map((g) => g.department).filter(Boolean))).sort();
  const allItems = d.flatMap((g) => g.items);
  const summary = {
    needing: d.filter((g) => g.items.some((i) => i.status !== 'completed')).length,
    high: allItems.filter((i) => i.priority === 'high').length,
    assigned: allItems.filter((i) => i.status === 'assigned').length,
    completed: allItems.filter((i) => i.status === 'completed').length,
  };
  const groups = d.map((g) => ({ ...g, items: g.items.filter((i) => (prio === 'all' || i.priority === prio) && (status === 'all' || i.status === status)) }))
    .filter((g) => g.items.length > 0 && (dept === 'all' || g.department === dept) &&
      (!q || g.employee.toLowerCase().includes(q.toLowerCase()) || g.role.toLowerCase().includes(q.toLowerCase())));
  const exportCsv = () => {
    const rows = [['Employee', 'Department', 'Role', 'Risk', 'Topic', 'Priority', 'Recommendation', 'Status']];
    d.forEach((g) => g.items.forEach((i) => rows.push([g.employee, g.department, g.role, g.risk_score ?? '', i.topic, i.priority, i.recommendation, i.status])));
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a'); a.href = url; a.download = 'morphphish-training.csv'; a.click(); URL.revokeObjectURL(url);
  };
  return (
    <>
      <Head eyebrow="Corrective guidance" title="Training" sub="Personalized awareness actions, derived from how each persona handled simulations — assign them and track completion." />
      <section className="grid4">
        <Metric label="Need training" value={summary.needing} />
        <Metric label="High priority" value={summary.high} />
        <Metric label="Assigned" value={summary.assigned} />
        <Metric label="Completed" value={summary.completed} />
      </section>
      <div className="card form" style={{ flexWrap: 'wrap', marginTop: 16 }}>
        <input style={{ minWidth: 200, flex: 1 }} value={q} onChange={(x) => setQ(x.target.value)} placeholder="Search name or role…" />
        <select value={dept} onChange={(x) => setDept(x.target.value)} title="Department">
          <option value="all">All departments</option>{depts.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
        <select value={prio} onChange={(x) => setPrio(x.target.value)} title="Priority">
          <option value="all">All priorities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
        </select>
        <select value={status} onChange={(x) => setStatus(x.target.value)} title="Status">
          <option value="all">Any status</option><option value="none">Not assigned</option><option value="assigned">Assigned</option><option value="completed">Completed</option>
        </select>
        <button className="secondary" onClick={exportCsv}>Export CSV</button>
      </div>
      <p className="muted" style={{ fontSize: 13, margin: '2px 2px 8px' }}>{groups.length} of {d.length} personas</p>
      <div className="stack">
        {groups.length === 0 ? <Empty>No training items match these filters.</Empty>
          : groups.map((g) => <TrainingCard key={g.employee_id} g={g} onAssign={onAssign} onComplete={onComplete} onRemove={onRemove} />)}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ system */

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

  // Once completed (submitted/reported), the backend retires the link (410) — and
  // a 404 means the session never existed. Either way, show a neutral ended card.
  if (e) return (
    <div className="loginwrap">
      <div className="logincard" style={{ textAlign: 'center' }}>
        <div className="loginbrand" style={{ color: 'var(--muted)' }}>MorphPhish</div>
        <h2>This link is no longer active</h2>
        <p className="muted">This authorized security-awareness simulation has already been completed, or the link is not valid. If you have questions, contact your security team.</p>
      </div>
    </div>
  );
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
          <p className="muted small">This was part of an authorized, non-punitive training exercise using synthetic data. Questions go to your security team. This link is now closed.</p>
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
function Console() {
  const { authed } = useAuth();
  if (!authed) return <Login />;
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/employees" element={<Employees />} />
        <Route path="/employees/:id" element={<Employee />} />
        <Route path="/simulations" element={<Simulations />} />
        <Route path="/archive" element={<Archive />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/recommendations" element={<Training />} />
      </Routes>
    </Layout>
  );
}
function App() {
  return (
    <Routes>
      {/* recipient-facing simulation link stays public — recipients are not admins */}
      <Route path="/simulate/:sid" element={<Sim />} />
      <Route path="*" element={<Console />} />
    </Routes>
  );
}
createRoot(document.getElementById('root')).render(
  <ThemeProvider><ToastProvider><AuthProvider><BrowserRouter><App /></BrowserRouter></AuthProvider></ToastProvider></ThemeProvider>
);
