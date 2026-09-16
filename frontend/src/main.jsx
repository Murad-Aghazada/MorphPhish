import React,{useEffect,useState} from 'react';
import{createRoot}from'react-dom/client';
import{BrowserRouter,Routes,Route,NavLink,useParams}from'react-router-dom';
import{BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer}from'recharts';
import{api}from'./api';
import'./styles.css';

const nav=['/','/employees','/simulations','/analytics','/recommendations','/status'];
const names=['Dashboard','Employees','Simulations','Analytics','Training','System'];
function Layout({children}){return <><aside><h2>RiskIntern<br/><span>PhishSim</span></h2>{nav.map((x,i)=><NavLink key={x} to={x} end={x==='/'}>{names[i]}</NavLink>)}</aside><main>{children}</main></>}
function useLoad(path){const[d,setD]=useState(null),[e,setE]=useState('');useEffect(()=>{api(path).then(setD).catch(x=>setE(x.message))},[path]);return[d,e,setD]}
const Box=({title,value})=><div className="card metric"><small>{title}</small><strong>{value}</strong></div>;
const Load=()=> <p>Loading…</p>;const Err=({e})=><div className="error">{e}</div>;

function Dashboard(){const[a,e]=useLoad('/analytics');if(e)return <Err e={e}/>;if(!a)return <Load/>;return <><h1>Security Awareness Dashboard</h1><p className="muted">Synthetic, authorized simulation data</p><section className="grid4"><Box title="Delivery rate" value={`${a.delivery_rate}%`}/><Box title="Click rate" value={`${a.click_rate}%`}/><Box title="Submission rate" value={`${a.submission_rate}%`}/><Box title="Reporting rate" value={`${a.reporting_rate}%`}/></section><div className="card"><h3>Average risk by department</h3><ResponsiveContainer width="100%" height={320}><BarChart data={a.by_department}><XAxis dataKey="department"/><YAxis domain={[0,100]}/><Tooltip/><Bar dataKey="average_risk"/></BarChart></ResponsiveContainer></div></>}

function Employees(){const[d,e]=useLoad('/employees');if(e)return <Err e={e}/>;if(!d)return <Load/>;return <><h1>Employees</h1><div className="card"><table><thead><tr><th>Name</th><th>Department</th><th>Role</th><th>Language</th><th></th></tr></thead><tbody>{d.map(x=><tr key={x.id}><td>{x.full_name}</td><td>{x.department}</td><td>{x.role}</td><td>{x.preferred_language}</td><td><NavLink to={`/employees/${x.id}`}>View</NavLink></td></tr>)}</tbody></table></div></>}
function Employee(){const{id}=useParams();const[e,er]=useLoad('/employees/'+id);const[r]=useLoad('/employees/'+id+'/risk');const[c]=useLoad('/employees/'+id+'/context');if(er)return <Err e={er}/>;if(!e||!r||!c)return <Load/>;return <><h1>{e.full_name}</h1><section className="grid2"><div className="card"><h3>Persona</h3><p>{e.department} · {e.role}</p><p>Language: {e.preferred_language}</p></div><div className="card"><h3>Risk profile</h3><div className={'pill '+r.level}>{r.level} · {r.score}/100</div><pre>{JSON.stringify(r.factors,null,2)}</pre></div></section><div className="card"><h3>Synthetic operational context</h3>{c.map(x=><div className="context" key={x.id}><b>{x.kind}: {x.title}</b><p>{x.summary}</p></div>)}</div></>}

// ---- Unified Simulations workspace: generate → review/edit → approve → launch ----
const EDITABLE=new Set(['REVIEW_REQUIRED','GENERATED','DRAFT']);
function ScenarioCard({s,onChange}){
  const[edit,setEdit]=useState(false);
  const[f,setF]=useState({subject:s.subject,email_body:s.email_body,pretext:s.pretext,landing_page_message:s.landing_page_message});
  const[msg,setMsg]=useState('');const[launch,setLaunch]=useState(null);
  const editable=EDITABLE.has(s.status);
  async function save(){try{await api(`/scenarios/${s.id}`,{method:'PATCH',body:JSON.stringify(f)});setEdit(false);setMsg('Saved.');onChange()}catch(x){setMsg(x.message)}}
  async function act(path){try{await api(`/scenarios/${s.id}/${path}`,{method:'POST'});setMsg('');onChange()}catch(x){setMsg(x.message)}}
  async function regen(){try{await api('/scenarios/generate',{method:'POST',body:JSON.stringify({employee_id:s.employee_id,objective:s.objective,difficulty:s.difficulty})});setMsg('Generated a fresh version below — reject this one if unwanted.');onChange()}catch(x){setMsg(x.message)}}
  async function doLaunch(){try{const r=await api(`/scenarios/${s.id}/launch`,{method:'POST',body:JSON.stringify({})});setLaunch(r);setMsg('');onChange()}catch(x){setMsg(x.message)}}
  return <div className="card">
    <div className="row"><h3>{s.subject}</h3><span className={'pill status-'+s.status.toLowerCase()}>{s.status.replace('_',' ')}</span></div>
    {edit
      ? <div className="editform">
          <label>Subject</label><input value={f.subject} onChange={e=>setF({...f,subject:e.target.value})}/>
          <label>Email body</label><textarea rows={4} value={f.email_body} onChange={e=>setF({...f,email_body:e.target.value})}/>
          <label>Pretext (cover story)</label><textarea rows={2} value={f.pretext} onChange={e=>setF({...f,pretext:e.target.value})}/>
          <label>Landing page — must contain the words “simulation” and “password”</label><textarea rows={2} value={f.landing_page_message} onChange={e=>setF({...f,landing_page_message:e.target.value})}/>
          <div className="actions"><button onClick={save}>Save</button><button className="secondary" onClick={()=>setEdit(false)}>Cancel</button></div>
        </div>
      : <><p><b>Email:</b> {s.email_body}</p><p><b>Pretext:</b> {s.pretext}</p><p><b>Landing:</b> {s.landing_page_message}</p><p className="muted">Risk cues: {(s.risk_indicators||[]).join(', ')}</p></>}
    {!edit&&<div className="actions">
      {editable&&<button className="secondary" onClick={()=>setEdit(true)}>Edit</button>}
      {editable&&<button className="secondary" onClick={regen}>Regenerate</button>}
      {s.status==='REVIEW_REQUIRED'&&<button onClick={()=>act('approve')}>Approve</button>}
      {editable&&<button className="secondary" onClick={()=>act('reject')}>Reject</button>}
      {s.status==='APPROVED'&&<button onClick={doLaunch}>Launch simulation</button>}
    </div>}
    {launch&&<div className="notice launched">Launched. Simulation link:&nbsp;<a href={launch.simulation_url} target="_blank" rel="noreferrer">{launch.simulation_url}</a>&nbsp;<button className="secondary" onClick={()=>navigator.clipboard&&navigator.clipboard.writeText(launch.simulation_url)}>Copy</button></div>}
    {msg&&<p className="muted">{msg}</p>}
  </div>;
}
function Simulations(){
  const[scen,e,setScen]=useLoad('/scenarios');const[emps]=useLoad('/employees');
  const[emp,setEmp]=useState('');const[obj,setObj]=useState('Recognize contextual social-engineering cues');const[diff,setDiff]=useState('medium');
  const[msg,setMsg]=useState('');const[busy,setBusy]=useState(false);
  const refresh=async()=>setScen(await api('/scenarios'));
  async function gen(){setBusy(true);setMsg('');try{await api('/scenarios/generate',{method:'POST',body:JSON.stringify({employee_id:emp,objective:obj,difficulty:diff})});await refresh();setMsg('Message generated — review it below, then approve to launch.')}catch(x){setMsg(x.message)}setBusy(false)}
  if(e)return <Err e={e}/>;
  return <><h1>Simulations</h1><p className="muted">Generate a message → review &amp; edit → approve → launch. Everything uses synthetic, authorized data.</p>
    <div className="card form">
      <select value={emp} onChange={x=>setEmp(x.target.value)}><option value="">Select synthetic employee</option>{emps?.map(x=><option value={x.id} key={x.id}>{x.full_name} — {x.department}</option>)}</select>
      <input style={{minWidth:280,flex:1}} value={obj} onChange={x=>setObj(x.target.value)} placeholder="Objective"/>
      <select value={diff} onChange={x=>setDiff(x.target.value)}><option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option></select>
      <button disabled={!emp||busy} onClick={gen}>{busy?'Generating…':'Generate message'}</button>
      <span>{msg}</span>
    </div>
    {scen===null?<Load/>:scen.length===0?<p className="muted">No scenarios yet — generate one above.</p>:scen.map(s=><ScenarioCard key={s.id} s={s} onChange={refresh}/>)}
  </>;
}

function Analytics(){const[d,e]=useLoad('/analytics');if(e)return <Err e={e}/>;if(!d)return <Load/>;return <><h1>Analytics</h1><section className="grid4"><Box title="Targets" value={d.targets}/><Box title="Open rate" value={`${d.open_rate}%`}/><Box title="Click rate" value={`${d.click_rate}%`}/><Box title="Avg response" value={`${d.average_response_time_seconds}s`}/></section><div className="card"><pre>{JSON.stringify(d,null,2)}</pre></div></>}
function Recs(){const[d,e]=useLoad('/recommendations');if(e)return <Err e={e}/>;return <><h1>Training Recommendations</h1>{d?.map((x,i)=><div className="card" key={i}><b>{x.employee} · {x.topic}</b><span className="pill">{x.priority}</span><p>{x.recommendation}</p></div>)}</>}
function Status(){const[d,e]=useLoad('/health');return <><h1>System / Integration Status</h1>{e?<Err e={e}/>:<div className="card"><pre>{JSON.stringify(d,null,2)}</pre><p>Mock mode exercises the same service interfaces as real integrations.</p></div>}</>}

function Sim(){const{sid}=useParams();const[d,e]=useLoad('/simulation/'+sid);const[msg,setMsg]=useState('');async function ev(type,pw){try{await api(`/simulation/${sid}/event`,{method:'POST',body:JSON.stringify({session_id:sid,event_type:type,password:pw})});setMsg('Safe event recorded. Any entered value was discarded and was not persisted.')}catch(x){setMsg(x.message)}}if(e)return <main><Err e={e}/></main>;if(!d)return <main><Load/></main>;return <main className="landing"><div className="notice">AUTHORIZED SECURITY-AWARENESS SIMULATION</div><h1>Simulation Landing Page</h1><p>{d.message}</p><button onClick={()=>ev('link_clicked')}>Record link click</button><button onClick={()=>ev('form_viewed')}>View simulated sign-in form</button><div className="card"><label>Simulation value only — do not enter a real password</label><input id="pw" type="password" placeholder="Use a fake demo value"/><button onClick={()=>ev('credential_simulation_submitted',document.getElementById('pw').value)}>Submit simulation</button></div><button className="secondary" onClick={()=>ev('simulation_reported')}>Report this simulation</button><p>{msg}</p></main>}

function App(){return <Routes><Route path="/simulate/:sid" element={<Sim/>}/><Route path="*" element={<Layout><Routes><Route path="/" element={<Dashboard/>}/><Route path="/employees" element={<Employees/>}/><Route path="/employees/:id" element={<Employee/>}/><Route path="/simulations" element={<Simulations/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="/recommendations" element={<Recs/>}/><Route path="/status" element={<Status/>}/></Routes></Layout>}/></Routes>}
createRoot(document.getElementById('root')).render(<BrowserRouter><App/></BrowserRouter>);
