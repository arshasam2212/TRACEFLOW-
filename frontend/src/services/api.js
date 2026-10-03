const BASE_URL = 'https://traceflow-r1vm.onrender.com'

const j = async (u, o) => {
  let r

  try {
    r = await fetch(BASE_URL + '/api' + u, o)
  } catch {
    throw new Error(
      'Cannot reach the TRACEFLOW backend. Is the Render backend running?'
    )
  }

  if (!r.ok) {
    let m = 'Request failed'

    try {
      m = (await r.json()).detail || m
    } catch {}

    throw new Error(m)
  }

  return r.json()
}

export const api = {
  // Dashboard
  stats: () => j('/dashboard/stats'),

  // Demo scenarios
  scenarios: () => j('/scenarios'),

  // Networks
  networks: (q = '') => j('/networks' + q),
  network: (id) => j('/networks/' + id),

  // Accounts
  account: (a) => j('/accounts/' + a),
  flow: (a) => j(`/accounts/${a}/flow`),
  replay: (a) => j(`/accounts/${a}/replay`),

  // Investigations
  inv: (id) => j('/investigations/' + id),

  // AI / Evidence explanation
  explain: (id) =>
    j(`/investigations/${id}/explanation`),

  // What-if simulation
  whatif: (id, account) =>
    j(`/investigations/${id}/what-if`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        account,
      }),
    }),

  // CSV Upload
  upload: (f) => {
    const fd = new FormData()

    fd.append('file', f)

    return j('/transactions/upload', {
      method: 'POST',
      body: fd,
    })
  },

  // Investigation dossier PDF
  dossierUrl: (id, acc, remove) =>
    `${BASE_URL}/api/investigations/${id}/dossier?` +
    new URLSearchParams({
      ...(acc && { account: acc }),
      ...(remove && { remove }),
    }),
}