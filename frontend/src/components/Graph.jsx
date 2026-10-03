import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import { Maximize2, RotateCcw } from 'lucide-react'
import { inr, when } from '../utils/format'

export default function Graph({ elements, highlight = {}, onNode, height = 460 }) {
  const ref = useRef(), cy = useRef(), [tip, setTip] = useState(null)
  useEffect(() => {
    cy.current?.destroy()
    const mx = Math.max(1, ...elements.edges.map(e => e.data.amount))
    const c = cy.current = cytoscape({
      container: ref.current, elements: [...elements.nodes, ...elements.edges.map(e => ({ ...e, classes: 'sus' }))], minZoom: .3, maxZoom: 3,
      style: [
        { selector: 'node', style: { label: 'data(label)', 'font-size': 10, color: '#cbd5e1', 'background-color': '#3b82f6', 'text-valign': 'bottom', 'text-margin-y': 5, width: 22, height: 22, 'border-width': 1, 'border-color': '#93c5fd' } },
        { selector: 'node[?key]', style: { 'background-color': '#f97316', width: 30, height: 30, 'border-color': '#fdba74' } },
        { selector: 'edge', style: { width: `mapData(amount,0,${mx},1.5,7)`, 'line-color': '#475569', 'target-arrow-color': '#475569', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', opacity: .8 } },
        { selector: 'edge.sus', style: { 'line-color': '#c2703a', 'target-arrow-color': '#c2703a' } },
        { selector: 'edge.done', style: { 'line-color': '#38bdf8', 'target-arrow-color': '#38bdf8' } },
        { selector: 'edge.active', style: { 'line-color': '#f8fafc', 'target-arrow-color': '#f8fafc', width: 8, opacity: 1 } },
        { selector: 'node.done', style: { 'background-color': '#38bdf8' } },
        { selector: 'node.active', style: { 'background-color': '#f8fafc', width: 34, height: 34 } }],
      layout: { name: elements.nodes.length > 14 ? 'cose' : 'circle', animate: false, padding: 40 } })
    c.on('mouseover', 'edge', e => { const d = e.target.data(); setTip(`${d.id}: ${d.source} → ${d.target} · ${inr(d.amount)} · ${d.bank_s}→${d.bank_r} · ${when(d.timestamp)}`) })
    c.on('mouseout', 'edge', () => setTip(null))
    c.on('tap', 'node', e => onNode?.(e.target.id()))
    return () => c.destroy()
  }, [elements])
  useEffect(() => {
    const c = cy.current; if (!c) return
    c.elements().removeClass('done active')
    ;(highlight.done || []).forEach(id => c.getElementById(id).addClass('done'))
    ;(highlight.nodes || []).forEach(id => c.getElementById(id).addClass('done'))
    if (highlight.active) { const e = c.getElementById(highlight.active); e.addClass('active'); e.connectedNodes().addClass('active') }
  }, [highlight])
  return (
    <div className="relative">
      <div ref={ref} style={{ height }} className="rounded-xl bg-[#050912] border border-white/10" />
      <div className="absolute top-2 right-2 flex gap-1">
        <button title="Fit" className="p-2 glass" onClick={() => cy.current.fit(undefined, 40)}><Maximize2 size={14} /></button>
        <button title="Reset view" className="p-2 glass" onClick={() => { cy.current.zoom(1); cy.current.layout({ name: elements.nodes.length > 14 ? 'cose' : 'circle', animate: false, padding: 40 }).run() }}><RotateCcw size={14} /></button>
      </div>
      {tip && <div className="absolute bottom-2 left-2 right-2 glass px-3 py-2 text-xs mono bg-black/70">{tip}</div>}
    </div>)
}
