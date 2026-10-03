export const inr = n => n >= 1e7 ? `₹${(n / 1e7).toFixed(2)}Cr` : n >= 1e5 ? `₹${(n / 1e5).toFixed(1)}L` : `₹${Math.round(n).toLocaleString('en-IN')}`
export const clock = s => [Math.floor(s / 3600), Math.floor(s / 60) % 60, Math.floor(s % 60)].map(x => String(x).padStart(2, '0')).join(':')
export const when = t => t.replace('T', ' ')
export const LEVEL = { HIGH: 'text-orange-300 bg-orange-500/15 border-orange-400/40', MEDIUM: 'text-amber-200 bg-amber-400/10 border-amber-300/30', LOW: 'text-sky-200 bg-sky-400/10 border-sky-300/30' }
