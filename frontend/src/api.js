const RAW = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const BASE = RAW.replace(/\/$/, '');
const TOKEN_KEY = 'mp-token';

let TOKEN = '';
try { TOKEN = sessionStorage.getItem(TOKEN_KEY) || ''; } catch { /* private mode */ }

export function setToken(t) {
  TOKEN = t || '';
  try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ }
}
export function getToken() { return TOKEN; }

// Turn a FastAPI error body into one readable sentence.
// `detail` is a string for our HTTPExceptions, or an array of
// {loc, msg, ...} for 422 request-validation errors.
function readDetail(body, status) {
  const d = body && body.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d
      .map((e) => {
        const field = Array.isArray(e.loc) ? e.loc.filter((p) => p !== 'body').join('.') : '';
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join(' · ');
  }
  return `Request failed (HTTP ${status}).`;
}

export async function api(path, opts = {}) {
  let r;
  try {
    r = await fetch(BASE + path, {
      headers: {
        'Content-Type': 'application/json',
        ...(TOKEN ? { Authorization: 'Bearer ' + TOKEN } : {}),
        ...(opts.headers || {}),
      },
      ...opts,
    });
  } catch {
    throw new Error("Can't reach the server. Is the backend running?");
  }
  if (!r.ok) {
    // An expired/invalid session anywhere but the login call signs the admin out.
    if (r.status === 401 && path !== '/auth/login') {
      setToken('');
      try { window.dispatchEvent(new Event('mp-unauthorized')); } catch { /* non-browser */ }
    }
    let body = {};
    try { body = await r.json(); } catch { /* non-JSON error body */ }
    throw new Error(readDetail(body, r.status));
  }
  if (r.status === 204) return null;
  return r.json();
}
