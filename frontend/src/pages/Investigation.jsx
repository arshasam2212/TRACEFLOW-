import { useEffect, useState } from 'react'
import { Download, Bot, FlaskConical } from 'lucide-react'
import { api } from '../services/api'
import { Card, Badge, Btn, Err, Spin } from '../components/ui'
import Graph from '../components/Graph'
import { inr, when } from '../utils/format'

export default function Investigation({ netId, follow }) {
  const [d, setD] = useState(), [err, setErr] = useState(''), [ex, setEx] = useState(), [w, setW] = useState(), [rm, setRm] = useState('')
  useEffect(() => { setD(null); setEx(null); setW(null); if (netId) api.inv(netId).then(x => { setD(x); setRm(x.key_intermediary) }).catch(e => setErr(e.message)) }, [netId])
  if (!netId) return <Card><p className="text-slate-400 text-sm">Open a case from the dashboard or Network Explorer.</p></Card>
  if (err) return <Err m={err} />
  if (!d) return <Spin />
  const R = d.risk, dn = d.dna, yn = b => b ? 'YES' : 'NO'
  const sim = async () => { try { setW(await api.whatif(netId, rm)) } catch (e) { setErr(e.message) } }
  const ask = async () => { try { setEx(await api.explain(netId)) } catch (e) { setErr(e.message) } }
  return (
    <div className="space-y-4">
      <div className="grid lg:grid-cols-3 gap-4">
        <Card title={`CASE ${d.case_id}`}><div className="text-xs text-slate-400">Investigation Priority</div>
          <div className="text-5xl font-semibold mono my-1">{R.score}<span className="text-xl text-slate-500"> / 100</span></div><Badge level={R.level} />
          <div className="mt-4 space-y-2">{R.factors.map(f => <div key={f.name} className="text-xs"><div className="flex justify-between"><span>{f.name}</span><span className="mono">{f.score}/{f.max}</span></div>
            <div className="h-1.5 bg-white/10 rounded"><div className="h-full rounded bg-sky-400" style={{ width: `${f.score / f.max * 100}%` }} /></div></div>)}</div>
          <p className="text-[11px] text-slate-500 mt-3">{R.disclaimer}</p></Card>
        <Card title="Why flagged?" className="lg:col-span-1"><div className="space-y-2">{d.evidence.map(e => <div key={e} className="text-sm rounded-lg border border-emerald-400/20 bg-emerald-400/5 px-3 py-2">✓ {e}</div>)}</div></Card>
        <Card title="Network DNA"><div className="mono text-sm space-y-1">
          <div>Accounts: {dn.accounts}</div><div>Transactions: {dn.transactions}</div><div>Circularity: {dn.circularity}%</div><div>Velocity: {dn.velocity}</div>
          <div>Amount retention: {dn.retention != null ? dn.retention + '%' : 'n/a'}</div><div>Cross-bank: {yn(dn.cross_bank)}</div><div>Smurfing: {yn(dn.smurfing)}</div><div>Mule-chain: {yn(dn.mule_chain)}</div></div>
          <div className="mt-4 text-xs text-slate-400">Avg delay {d.velocity.avg_delay_seconds}s · median {d.velocity.median_delay_seconds}s · burst {d.velocity.burst_max_per_minute}/min</div></Card>
      </div>
      <Card title="Reconstructed network" right={<Btn onClick={() => follow(d.accounts[0].account_id)}>FOLLOW THE MONEY</Btn>}><Graph elements={d.elements} height={360} /></Card>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="What if? (simulation)"><div className="flex gap-2 items-center"><select value={rm} onChange={e => setRm(e.target.value)} className="bg-[#0b1220] border border-white/10 rounded-lg px-2 py-2 text-sm mono">
          {d.accounts.map(a => <option key={a.account_id} value={a.account_id}>{a.account_id} ({a.role})</option>)}</select><Btn onClick={sim}><FlaskConical size={14} className="inline mr-1" />REMOVE ACCOUNT</Btn></div>
          {w && <div className="mt-3 text-sm pop"><div className="text-[11px] text-amber-300 mb-2">{w.label}</div>
            <table className="w-full"><tbody>{[['Network connectivity', '100%', w.connectivity_after + '%'], ['Cycles', w.before.cycles, w.after.cycles], ['Paths', w.before.paths, w.after.paths], ['Reachable accounts (pairs)', w.before.reachable_pairs, w.after.reachable_pairs], ['Components', w.before.components, w.after.components]].map(r =>
              <tr key={r[0]} className="border-t border-white/5"><td className="py-1">{r[0]}</td><td className="mono text-slate-400">Before: {r[1]}</td><td className="mono text-sky-200">After: {r[2]}</td></tr>)}</tbody></table>
            <p className="mt-2 text-xs text-slate-400">Flow disrupted: {w.disrupted_transactions} of {w.total_transactions} transactions · {inr(w.disrupted_amount)}</p></div>}</Card>
        <Card title="AI Investigator" right={<Btn onClick={ask}><Bot size={14} className="inline mr-1" />EXPLAIN</Btn>}>
          {ex ? <div className="pop"><p className="text-sm leading-relaxed text-slate-200">{ex.text}</p><p className="text-[11px] text-slate-500 mt-2">Source: {ex.source === 'template' ? 'deterministic evidence template (no LLM)' : 'local LLM rewording of detected evidence'}</p></div>
            : <p className="text-sm text-slate-400">Generates a plain-language explanation from the detected evidence only.</p>}</Card>
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="Transaction timeline"><div className="max-h-80 overflow-y-auto text-xs mono space-y-1">{d.timeline.map(t => <div key={t.transaction_id} className="flex gap-2 border-l border-sky-500/40 pl-2"><span className="text-slate-500 w-36 shrink-0">{when(t.timestamp)}</span><span>{t.sender_account}→{t.receiver_account}</span><span className="ml-auto text-sky-200">{inr(t.amount)}</span></div>)}</div></Card>
        <Card title="Connected accounts"><div className="max-h-80 overflow-y-auto grid sm:grid-cols-2 gap-2">{d.accounts.map(a => <div key={a.account_id} className="text-xs rounded-lg border border-white/10 p-2"><b className="mono text-sm">{a.account_id}</b><div className="text-slate-400">{a.bank} · {a.role}</div></div>)}</div></Card>
      </div>
      <div className="glass p-6 text-center pop"><a href={api.dossierUrl(netId, d.key_intermediary, rm)} className="inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-orange-600 hover:bg-orange-500 font-semibold"><Download size={16} />GENERATE DOSSIER (PDF)</a>
        <div className="mt-6 text-lg md:text-2xl font-semibold tracking-[.15em] text-sky-200">FROM TRANSACTION ALERT TO RECONSTRUCTED MONEY FLOW</div></div>
    </div>)
}
