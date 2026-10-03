import { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { Card, Badge, Err, Spin, Btn } from '../components/ui'
import Graph from '../components/Graph'
import { inr } from '../utils/format'
const Sel = ({ v, set, opts, label }) => (
  <label className="text-xs text-slate-400 block">{label}
    <select value={v} onChange={e => set(e.target.value)} className="mt-1 w-full bg-[#0b1220] border border-white/10 rounded-lg px-2 py-1.5 text-sm text-slate-200">
      {opts.map(o => <option key={o[0]} value={o[0]}>{o[1]}</option>)}</select></label>)

export default function Explorer({ netId, setNet, openInv, version }) {
  const [f, setF] = useState({ pattern: '', bank: '', risk: '', min: 0, win: 0 })
  const [list, setList] = useState([]), [net, setN] = useState(), [acct, setAcct] = useState(), [err, setErr] = useState('')
  const q = '?' + new URLSearchParams({ ...(f.pattern && { pattern: f.pattern }), ...(f.bank && { bank: f.bank }), ...(f.risk && { risk: f.risk }) })
  useEffect(() => { api.networks(q).then(setList).catch(e => setErr(e.message)) }, [q, version])
  useEffect(() => { setAcct(null); if (netId) api.network(netId).then(setN).catch(e => setErr(e.message)); else setN(null) }, [netId, version])
  const els = useMemo(() => {
    if (!net) return null
    const t0 = Date.parse(net.elements.edges[0]?.data.timestamp || 0)
    const edges = net.elements.edges.filter(e => e.data.amount >= f.min && (!+f.win || (Date.parse(e.data.timestamp) - t0) / 1000 <= +f.win))
    const used = new Set(edges.flatMap(e => [e.data.source, e.data.target]))
    return { nodes: net.elements.nodes.filter(n => used.has(n.data.id)), edges }
  }, [net, f.min, f.win])
  useEffect(() => { if (acct) api.account(acct.id).then(a => setAcct({ id: acct.id, ...a })).catch(() => { }) }, [acct?.id])
  return (
    <div className="grid lg:grid-cols-[280px_1fr] gap-4">
      <div className="space-y-3">
        <Card title="Filters"><div className="space-y-3">
          <Sel label="Pattern" v={f.pattern} set={v => setF({ ...f, pattern: v })} opts={[['', 'All'], ['circular_flow', 'Circular'], ['mule_chain', 'Mule chain'], ['smurfing', 'Smurfing']]} />
          <Sel label="Bank" v={f.bank} set={v => setF({ ...f, bank: v })} opts={[['', 'All'], ...['A', 'B', 'C', 'D', 'E'].map(x => ['BANK_' + x, 'BANK_' + x])]} />
          <Sel label="Risk level" v={f.risk} set={v => setF({ ...f, risk: v })} opts={[['', 'All'], ['HIGH', 'High'], ['MEDIUM', 'Medium'], ['LOW', 'Low']]} />
          <Sel label="Time window (from first tx)" v={f.win} set={v => setF({ ...f, win: v })} opts={[[0, 'All'], [120, '2 min'], [600, '10 min'], [3600, '1 hour']]} />
          <label className="text-xs text-slate-400 block">Minimum amount: {inr(f.min)}<input type="range" min="0" max="1000000" step="10000" value={f.min} onChange={e => setF({ ...f, min: +e.target.value })} className="w-full" /></label>
        </div></Card>
        <Card title={`Networks (${list.length})`}><div className="max-h-[360px] overflow-y-auto space-y-1">
          {list.map(n => <button key={n.id} onClick={() => setNet(n.id)} className={`w-full text-left px-3 py-2 rounded-lg text-sm border ${n.id === netId ? 'border-sky-400/60 bg-sky-500/10' : 'border-white/5 hover:bg-white/5'}`}>
            <div className="flex justify-between"><span className="mono">{n.case_id}</span><Badge level={n.risk.level} /></div><div className="text-xs text-slate-400">{n.category} · {n.accounts} accounts · {inr(n.total_amount)}</div></button>)}</div></Card>
      </div>
      <div className="space-y-3">
        <Err m={err} />
        {!net ? <Card><p className="text-slate-400 text-sm">Select a suspicious network to reconstruct its transaction graph.</p></Card> : !els ? <Spin /> : <>
          <Card title={`${net.case_id} · ${net.category} network`} right={<Btn onClick={() => openInv(net.id)}>OPEN INVESTIGATION</Btn>}>
            <Graph elements={els} onNode={id => setAcct({ id })} height={470} />
            <p className="text-xs text-slate-500 mt-2">Orange node = key intermediary · edge thickness = amount · hover an edge for transaction details · click a node for the account.</p></Card>
          {acct?.account_id && <Card title={`Account ${acct.id}`}><div className="text-sm grid sm:grid-cols-4 gap-2">
            <div>Bank<br /><b>{acct.bank}</b></div><div>Sent<br /><b>{acct.sent_count} · {inr(acct.sent_total)}</b></div><div>Received<br /><b>{acct.received_count} · {inr(acct.received_total)}</b></div>
            <div>Risk<br /><b>{acct.risk ? `${acct.risk.score} ${acct.risk.level}` : '—'}</b></div></div></Card>}
        </>}
      </div>
    </div>)
}
