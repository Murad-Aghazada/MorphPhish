const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

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
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts,
    });
  } catch {
    throw new Error("Can't reach the server. Is the backend running?");
  }
  if (!r.ok) {
    let body = {};
    try {
      body = await r.json();
    } catch {
      /* non-JSON error body */
    }
    throw new Error(readDetail(body, r.status));
  }
  if (r.status === 204) return null;
  return r.json();
}
