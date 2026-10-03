import { LEVEL } from '../utils/format'
export const Card = ({ title, right, children, className = '' }) => (
  <section className={`glass p-5 pop ${className}`}>
    {(title || right) && <div className="flex items-center justify-between mb-3"><h3 className="text-[11px] tracking-[.2em] uppercase text-slate-400">{title}</h3>{right}</div>}
    {children}
  </section>)
export const Stat = ({ v, l, hot }) => (<div className="glass p-4 pop"><div className={`text-3xl font-semibold mono ${hot ? 'text-orange-300' : 'text-sky-200'}`}>{v}</div><div className="text-xs text-slate-400 mt-1">{l}</div></div>)
export const Badge = ({ level }) => <span className={`px-2 py-0.5 rounded border text-[11px] font-semibold ${LEVEL[level]}`}>{level}</span>
export const Btn = ({ children, className = '', ...p }) => <button {...p} className={`px-4 py-2 rounded-lg text-sm font-medium bg-sky-600 hover:bg-sky-500 disabled:opacity-40 transition ${className}`}>{children}</button>
export const Err = ({ m }) => m ? <div className="glass p-3 text-sm text-orange-200 border-orange-400/30">⚠ {m}</div> : null
export const Spin = () => <div className="text-sm text-slate-400 animate-pulse">Loading…</div>
