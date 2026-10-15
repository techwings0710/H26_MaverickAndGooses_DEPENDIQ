import { motion } from 'motion/react'
import { AlertTriangle, ArrowUpRight, Box, CircleCheck, GitBranch, LoaderCircle } from 'lucide-react'

export function Badge({children, tone = ''}) { return <span className={`badge ${tone}`}>{children}</span> }
export function Panel({children, className = '', ...props}) { return <motion.section initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:0.25}} className={`panel ${className}`} {...props}>{children}</motion.section> }
export function Busy({label}) { return <span className="busy"><LoaderCircle size={15} className="spin"/>{label}</span> }
export function Empty({title = 'Your next move starts with evidence.', text = 'Scan a local Python repository to inspect dependencies, trace usage, and build a migration plan.'}) { return <div className="empty"><div className="empty-icon"><GitBranch size={30}/></div><h2>{title}</h2><p>{text}</p></div> }
export function OutcomeCard({name, outcome}) { return <Panel className="outcome"><div className="row"><h3>{name}</h3><Badge tone={outcome?.status === 'PASSED' ? 'low' : 'unknown'}>{outcome?.status || 'NOT RUN'}</Badge></div><p>{outcome?.reason || 'Run verification to capture actual execution evidence.'}</p><div className="metric-row">{['passed','failed','skipped'].map(k=><div key={k}><strong>{outcome?.[k] ?? '—'}</strong><small>{k}</small></div>)}</div>{outcome?.python_version && <p className="mono">Python {outcome.python_version}</p>}{outcome?.commands?.length > 0 && <details><summary>Execution evidence · exit {outcome.exit_code ?? '—'}</summary><pre>{outcome.commands.map(c=>c.join(' ')).join('\n')}<br/>{outcome.output}</pre></details>}</Panel> }

export function DependencyGraph({dependencies, selected, onSelect}) {
  const visible = dependencies.slice(0, 10)
  return <div className="graph" aria-label="Observed repository to dependency relationships">
    <svg viewBox="0 0 720 290" role="img" aria-label="Manifest dependency relationship graph">
      <defs><linearGradient id="flow"><stop stopColor="#7662cd"/><stop offset="1" stopColor="#383441"/></linearGradient></defs>
      {visible.map((d,i)=>{const x=140 + i%5*110, y=i<5?65:230;return <path key={d.name} className="graph-line" d={`M 360 145 Q ${x} 145 ${x} ${y}`} stroke="url(#flow)" fill="none"/>})}
      <circle cx="360" cy="145" r="32" fill="#1c192d" stroke="#8b7cf8"/><text x="360" y="150" textAnchor="middle" fill="#d9d3ff" fontSize="12">REPO</text>
    </svg>
    {visible.map((d,i)=><button key={d.name} className={`graph-node ${d.risk_level} ${selected===d.name?'chosen':''}`} style={{left:`${(140+i%5*110)/7.2}%`,top:`${(i<5?65:230)/2.9}%`}} onClick={()=>onSelect(d.name)}><Box size={13}/>{d.name}</button>)}
    {!visible.length && <div className="graph-placeholder"><Box size={23}/><span>Real relationships appear after scanning</span></div>}
  </div>
}
