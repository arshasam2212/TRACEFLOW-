const j = async (u, o) => {
  let r
  try { r = await fetch('/api' + u, o) } catch { throw new Error('Cannot reach the TRACEFLOW backend. Is it running on port 8000?') }
  if (!r.ok) { let m = 'Request failed'; try { m = (await r.json()).detail || m } catch {} throw new Error(m) }
  return r.json()
}
export const api = {
  stats: () => j('/dashboard/stats'), scenarios: () => j('/scenarios'),
  networks: (q = '') => j('/networks' + q), network: id => j('/networks/' + id),
  account: a => j('/accounts/' + a), flow: a => j(`/accounts/${a}/flow`), replay: a => j(`/accounts/${a}/replay`),
  inv: id => j('/investigations/' + id), explain: id => j(`/investigations/${id}/explanation`),
  whatif: (id, account) => j(`/investigations/${id}/what-if`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account }) }),
  upload: f => { const fd = new FormData(); fd.append('file', f); return j('/transactions/upload', { method: 'POST', body: fd }) },
  dossierUrl: (id, acc, remove) => `/api/investigations/${id}/dossier?` + new URLSearchParams({ ...(acc && { account: acc }), ...(remove && { remove }) }),
}
