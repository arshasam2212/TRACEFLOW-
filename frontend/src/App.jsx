import { useEffect, useRef, useState } from 'react'
import { LayoutDashboard, Network, Route, FileSearch, Upload } from 'lucide-react'
import { api } from './services/api'
import Overview from './pages/Overview'
import Explorer from './pages/Explorer'
import Follow from './pages/Follow'
import Investigation from './pages/Investigation'

const TABS = [['overview', 'Overview', LayoutDashboard], ['explorer', 'Network Explorer', Network], ['follow', 'Follow the Money', Route], ['case', 'Investigation', FileSearch]]
export default function App() {
  const [page, setPage] = useState('overview'), [netId, setNetId] = useState(), [acct, setAcct] = useState(), [sc, setSc] = useState([])
  const [version, setVersion] = useState(0), [up, setUp] = useState(null), file = useRef()
  useEffect(() => { api.scenarios().then(setSc).catch(() => { }) }, [version])
  const openInv = id => { setNetId(id); setPage('case') }
  const follow = a => { setAcct(null); setTimeout(() => setAcct(a), 0); setPage('follow') }
  const scenario = e => {
    const s = sc.find(x => x.id === +e.target.value); e.target.value = ''; if (!s) return
    setNetId(s.network_id); if (s.id === 4 || s.id === 1 || s.id === 2 || s.id === 3 || s.id === 5) follow(s.account)
  }
  const upload = async e => {
    const f = e.target.files[0]; if (!f) return
    setUp({ busy: true, msg: 'Validating → building graph → running detectors…' })
    try { const r = await api.upload(f); setUp({ msg: `Loaded ${r.report.rows_valid.toLocaleString()} rows (${r.report.rows_dropped} skipped). ${r.stats.suspicious_networks} suspicious networks found.` }); setNetId(null); setVersion(v => v + 1); setPage('overview') }
    catch (x) { setUp({ err: x.message }) }
    e.target.value = ''
  }
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 backdrop-blur bg-[#060a14]/80 border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center gap-4">
          <div><div className="text-xl font-bold tracking-[.25em]"><span className="text-sky-400">TRACE</span>FLOW</div><div className="text-[10px] tracking-wider text-slate-400">Temporal Graph Intelligence for Financial Crime Investigation</div></div>
          <nav className="flex gap-1 flex-1 flex-wrap">{TABS.map(([k, l, I]) => <button key={k} onClick={() => setPage(k)} className={`px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition ${page === k ? 'bg-sky-500/15 text-sky-200' : 'text-slate-400 hover:text-slate-200'}`}><I size={15} />{l}</button>)}</nav>
          <select onChange={scenario} defaultValue="" className="bg-[#0b1220] border border-white/10 rounded-lg px-2 py-2 text-xs"><option value="">LOAD DEMO SCENARIO…</option>{sc.map(s => <option key={s.id} value={s.id}>{s.id}. {s.title}</option>)}</select>
          <button onClick={() => file.current.click()} className="px-3 py-2 rounded-lg text-xs bg-white/10 hover:bg-white/20 flex gap-2 items-center"><Upload size={14} />Upload CSV</button>
          <input ref={file} type="file" accept=".csv" hidden onChange={upload} />
        </div>
        {up && <div className={`text-xs px-4 py-1.5 text-center ${up.err ? 'bg-orange-500/20 text-orange-200' : 'bg-sky-500/10 text-sky-200'}`}>{up.busy && <div className="h-0.5 bg-sky-400 animate-pulse mb-1" />}{up.err ? '⚠ ' + up.err : up.msg}<button className="ml-3 underline" onClick={() => setUp(null)}>dismiss</button></div>}
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">
        {page === 'overview' && <Overview open={openInv} version={version} />}
        {page === 'explorer' && <Explorer netId={netId} setNet={setNetId} openInv={openInv} version={version} />}
        {page === 'follow' && <Follow account={acct} openInv={openInv} />}
        {page === 'case' && <Investigation netId={netId} follow={follow} />}
      </main>
      <footer className="text-center text-[11px] text-slate-500 pb-6">Results are suspicious patterns and investigation priorities — not findings of criminal conduct. Human review required.</footer>
    </div>)
}
