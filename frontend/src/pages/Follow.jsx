import { useEffect, useRef, useState } from 'react'
import { Play, Search } from 'lucide-react'
import { api } from '../services/api'
import { Card, Btn, Err, Spin } from '../components/ui'
import Graph from '../components/Graph'
import { inr, clock, when } from '../utils/format'

export default function Follow({ account: init, openInv }) {
  const [acc, setAcc] = useState(init || 'A101'), [f, setF] = useState(), [els, setEls] = useState(), [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  const [rp, setRp] = useState(null), [fr, setFr] = useState(), timer = useRef()
  const stop = () => { clearInterval(timer.current); setRp(null); setFr(null) }
  const run = async (a = acc) => {
    stop(); setErr(''); setF(null); setEls(null); setBusy(true)
    try { const r = await api.flow(a.trim()); setF(r); if (r.network_id) setEls((await api.network(r.network_id)).elements) } catch (e) { setErr(e.message) }
    setBusy(false)
  }
  useEffect(() => { if (init) { setAcc(init); run(init) } return () => clearInterval(timer.current) }, [init])
  const replay = async () => {
    stop()
    try {
      const r = await api.replay(acc.trim()); setFr(r); let i = 1; setRp(1)
      timer.current = setInterval(() => { i++; setRp(i); if (i >= r.frames.length) clearInterval(timer.current) }, 1100)
    } catch (e) { setErr(e.message) }
  }
  const frames = fr?.frames || [], cur = rp ? frames[rp - 1] : null, done = rp && rp >= frames.length
  const hl = rp ? { active: done ? null : cur.transaction_id, done: frames.slice(0, done ? rp : rp - 1).map(x => x.transaction_id), nodes: frames.slice(0, rp).flatMap(x => [x.sender_account, x.receiver_account]) } : {}
  const retention = cur ? (cur.amount / frames[0].amount * 100).toFixed(1) : null
  return (
    <div className="space-y-4">
      <Card title="Follow the Money"><div className="flex gap-2 max-w-xl">
        <input value={acc} onChange={e => setAcc(e.target.value)} onKeyDown={e => e.key === 'Enter' && run()} placeholder="Enter Account ID" className="flex-1 bg-[#0b1220] border border-white/10 rounded-lg px-3 py-2 mono" />
        <Btn onClick={() => run()} disabled={busy}><Search size={14} className="inline mr-1" />FOLLOW</Btn></div></Card>
      <Err m={err} />{busy && <Spin />}
      {f && !f.found && <Card title="No suspicious flow found"><p className="text-sm text-slate-300">{f.message}</p>
        {f.profile && <div className="mt-3 text-sm"><p className="font-semibold">High transaction volume detected.</p><p className="text-slate-400 mb-2">However:</p>
          {f.profile.checks.map(c => <div key={c.label} className={c.ok ? 'text-emerald-300' : 'text-orange-300'}>{c.ok ? '✓' : '✗'} {c.label} <span className="text-slate-500 text-xs">— {c.detail}</span></div>)}
          <p className="mt-3 text-sky-200 font-medium">Classification: {f.profile.classification}</p><p className="text-xs text-slate-500">{f.profile.note}</p></div>}</Card>}
      {f?.found && <div className="grid lg:grid-cols-[320px_1fr] gap-4">
        <Card title={`${f.case_id} · discovered path`}>
          <div className="mono text-sm">{f.steps.map((s, i) => <div key={s.transaction_id}>
            {i === 0 && <div className="text-sky-200">{s.sender_account}</div>}
            <div className="pl-3 text-slate-400 text-xs border-l border-slate-600 ml-1 py-1">↓ {inr(s.amount)} · {s.sender_bank}→{s.receiver_bank}</div>
            <div className="text-sky-200">{s.receiver_account}</div></div>)}</div>
          <div className="grid grid-cols-2 gap-2 text-xs mt-4">
            <div>Total moved<br /><b className="text-sm">{inr(f.summary.total_amount)}</b></div><div>Elapsed<br /><b className="text-sm">{clock(f.summary.elapsed_seconds)}</b></div>
            <div>Hops<br /><b className="text-sm">{f.summary.hops}</b></div><div>Retention<br /><b className="text-sm">{f.summary.retention_percent ?? 'n/a'}{f.summary.retention_percent != null && '%'}</b></div>
            <div className="col-span-2">Banks: {f.summary.banks.join(', ')}</div><div className="col-span-2">Patterns: {f.summary.patterns.join(', ')}</div></div>
          <div className="flex gap-2 mt-4"><Btn onClick={replay}><Play size={14} className="inline mr-1" />REPLAY FLOW</Btn><Btn className="bg-white/10 hover:bg-white/20" onClick={() => openInv(f.network_id)}>CASE</Btn></div>
        </Card>
        <Card title="Money-flow replay">
          {els && <Graph elements={els} highlight={hl} height={400} />}
          {cur && <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 mono text-sm pop">
            <div>Elapsed<br /><b className="text-sky-200">{clock(cur.offset_seconds)}</b></div><div>Hops<br /><b className="text-sky-200">{rp}</b></div>
            <div>Amount moved<br /><b className="text-sky-200">{inr(cur.cumulative_amount)}</b></div><div>{f.pattern === 'smurfing' ? 'Last amount' : 'Retention'}<br /><b className="text-sky-200">{f.pattern === 'smurfing' ? inr(cur.amount) : retention + '%'}</b></div>
            <div className="col-span-full text-xs text-slate-400">{when(cur.timestamp)} · {cur.sender_account} → {cur.receiver_account} · {inr(cur.amount)}</div></div>}
          {done && <div className="mt-3 text-center text-xl font-bold tracking-widest text-orange-300 pop">{fr.final_label}</div>}
        </Card></div>}
    </div>)
}
