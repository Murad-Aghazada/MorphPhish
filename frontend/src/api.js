const BASE=import.meta.env.VITE_API_URL||'http://localhost:8000/api/v1';
export async function api(path,opts={}){const r=await fetch(BASE+path,{headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts}); if(!r.ok){let x={};try{x=await r.json()}catch{};throw new Error(x.detail||`HTTP ${r.status}`)}; if(r.status===204)return null; return r.json()}
