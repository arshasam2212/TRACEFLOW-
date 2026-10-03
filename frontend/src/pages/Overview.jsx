import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../services/api'
import { Card, Stat, Badge, Err, Spin } from '../components/ui'
import { inr } from '../utils/format'
const COL = { Circular: '#38bdf8', Mule: '#818cf8', Smurfing: '#2dd4bf', Mixed: '#f97316' }

export default function Overview({ open, version }) {
  const [d, setD] = useState(), [err, setErr] = useState('')
  useEffect(() => { api.stats().then(setD).catch(e => setErr(e.message)) }, [version])
  if (err) return <Err m={err} />
  if (!d) return <Spin />
  const s = d.stats
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Stat v={s.transactions.toLocaleString()} l="Transactions Analyzed" /><Stat v={s.flagged_accounts} l="Flagged Accounts" hot />
        <Stat v={s.suspicious_networks} l="Suspicious Networks" hot /><Stat v={s.mule_chains} l="Mule Chains" /><Stat v={s.smurfing_rings} l="Smurfing Rings" />
      </div>
      <div className="grid lg:grid-cols-3 gap-4">
        <Card title="Suspicious Network Distribution" className="lg:col-span-1">
          <ResponsiveContainer width="100%" height={220}><BarChart data={s.distribution}><XAxis dataKey="name" stroke="#64748b" fontSize={11} /><YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
            <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #1e293b' }} /><Bar dataKey="count" radius={[6, 6, 0, 0]}>{s.distribution.map(x => <Cell key={x.name} fill={COL[x.name]} />)}</Bar></BarChart></ResponsiveContainer>
        </Card>
        <Card title={`High-volume accounts reviewed (${s.high_volume_cleared} cleared)`} className="lg:col-span-2">
          <p className="text-xs text-slate-400 mb-2">High transaction volume ≠ suspicious. Context decides.</p>
          <div className="grid sm:grid-cols-2 gap-2">{d.high_volume.map(b => (
            <div key={b.account} className="rounded-lg border border-white/10 p-3 text-xs">
              <div className="flex justify-between"><b className="mono">{b.account}</b><span className="text-slate-400">{b.transactions} tx · {b.counterparties} counterparties</span></div>
              <div className="text-sky-300 mt-1">{b.classification}</div></div>))}</div>
        </Card>
      </div>
      <Card title="Recent Investigations">
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-left text-xs text-slate-400"><tr>{['Case ID', 'Network', 'Pattern', 'Accounts', 'Amount', 'Priority', 'Status'].map(h => <th key={h} className="py-2 pr-4">{h}</th>)}</tr></thead>
          <tbody>{d.recent.map(n => (
            <tr key={n.id} onClick={() => open(n.id)} className="border-t border-white/5 hover:bg-white/5 cursor-pointer">
              <td className="py-2 pr-4 mono">{n.case_id}</td><td className="pr-4 mono">{n.id}</td><td className="pr-4">{n.category}</td><td className="pr-4">{n.accounts}</td>
              <td className="pr-4">{inr(n.total_amount)}</td><td className="pr-4"><span className="mono mr-2">{n.risk.score}</span><Badge level={n.risk.level} /></td><td>{n.status}</td></tr>))}</tbody></table></div>
      </Card>
    </div>)
}
