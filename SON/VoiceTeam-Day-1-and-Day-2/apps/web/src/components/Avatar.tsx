import { useEffect, useId, useRef, useState } from 'react';
import type { AgentProfile, AgentState } from '../lib/agents';

/** Pure visual state. Speaking is a labeled fixture, never an audio measurement. */
export function Avatar({ agent, state, motion }: { agent: AgentProfile; state: AgentState; motion: boolean }) {
  const id = useId().replace(/:/g, '');
  const ref = useRef<HTMLDivElement>(null);
  const [onScreen, setOnScreen] = useState(false);
  useEffect(() => {
    let frame = 0;
    const measure = () => {
      frame = 0;
      const rect = ref.current?.getBoundingClientRect();
      setOnScreen(Boolean(rect && rect.bottom > 0 && rect.top < window.innerHeight && rect.right > 0 && rect.left < window.innerWidth));
    };
    const update = () => { if (!frame) frame = requestAnimationFrame(measure); };
    measure();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => { cancelAnimationFrame(frame); window.removeEventListener('scroll', update); window.removeEventListener('resize', update); };
  }, []);
  const paint = `url(#${id}-color)`;
  const mouth = state === 'error' ? 'M87 114 Q100 102 113 114' : 'M87 108 Q100 123 113 108';
  return <div ref={ref} className={`avatar avatar-${agent.id} state-${state}`} data-animated={motion && onScreen} aria-hidden="true">
    <div className={`avatar-aura ${agent.gradient}`}/>
    <svg viewBox="0 0 200 200" className="avatar-svg" focusable="false">
      <defs>
        <linearGradient id={`${id}-color`} x1="0" y1="0" x2="1" y2="1"><stop stopColor={agent.from}/><stop offset="1" stopColor={agent.to}/></linearGradient>
        <radialGradient id={`${id}-body`} cx="35%" cy="25%" r="80%"><stop stopColor="#ffffff" stopOpacity=".98"/><stop offset=".3" stopColor={agent.from} stopOpacity=".85"/><stop offset="1" stopColor={agent.to}/></radialGradient>
      </defs>
      <g className="avatar-float">
        {agent.id === 'supervisor' && <>
          <circle cx="100" cy="100" r="64" fill={`url(#${id}-body)`} opacity=".96"/>
          <g className="orb-ribbons" fill="none" stroke={paint}>
            <ellipse cx="100" cy="100" rx="86" ry="54" strokeWidth="4" transform="rotate(-30 100 100)"/>
            <ellipse cx="100" cy="100" rx="85" ry="48" strokeWidth="2.5" transform="rotate(42 100 100)"/>
            <ellipse cx="100" cy="100" rx="82" ry="64" strokeWidth="1.5" transform="rotate(100 100 100)" opacity=".55"/>
          </g>
          <path d="M53 76C59 47 96 32 120 44" fill="none" stroke="white" strokeOpacity=".65" strokeWidth="5" strokeLinecap="round"/>
        </>}
        {agent.id === 'researcher' && <>
          <path d="M44 111C26 70 57 32 100 37C144 25 176 74 155 112L137 144L116 136L98 150L76 136L55 143Z" fill={`url(#${id}-body)`}/>
          <path d="M45 121Q22 151 50 164M154 115Q182 130 170 153" stroke={paint} strokeWidth="8" fill="none" strokeLinecap="round"/>
          <circle cx="73" cy="91" r="22" stroke="white" strokeOpacity=".8" strokeWidth="3" fill="none"/>
          <path d="m55 106-9 10" stroke="white" strokeWidth="5" strokeLinecap="round"/>
          <circle className="satellite" cx="158" cy="38" r="8" fill={paint}/>
        </>}
        {agent.id === 'solver' && <>
          <path d="M99 22C122 60 141 46 155 74C179 122 137 161 98 157C58 165 24 128 43 87C52 67 73 62 76 39L89 57Z" fill={`url(#${id}-body)`}/>
          <path d="m149 37-9 19h13l-8 20 25-29h-15l7-15" fill="#F59E0B"/>
          <path d="M47 61 32 55M31 76l-13 2" fill="none" stroke="#F43F5E" strokeWidth="4" strokeLinecap="round"/>
        </>}
        {agent.id === 'verifier' && <>
          <path d="M100 35C119 42 140 45 155 46L155 101C155 133 132 156 100 170C68 156 45 133 45 101L45 46C63 45 82 42 100 35Z" fill={`url(#${id}-body)`}/>
          <ellipse cx="100" cy="40" rx="55" ry="14" fill="none" stroke={paint} strokeWidth="3"/>
          <path d="m139 134 10 10 20-22" stroke="#15803D" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </>}
        <g className="avatar-eyes" fill="#27203D">
          {state === 'error' ? <g stroke="#27203D" strokeWidth="4" strokeLinecap="round"><path d="m73 83 11 10m0-10L73 93m44-10 11 10m0-10-11 10"/></g> : <>
            <ellipse cx="79" cy="89" rx="5.5" ry={agent.id === 'verifier' ? 4 : 8}/><ellipse cx="121" cy="89" rx="5.5" ry={agent.id === 'verifier' ? 4 : 8}/>
            <circle cx="81" cy="86" r="1.7" fill="white"/><circle cx="123" cy="86" r="1.7" fill="white"/>
          </>}
        </g>
        {state === 'speaking' ? <ellipse className="speaking-mouth" cx="100" cy="113" rx="9" ry="8" fill="#38274B"/> : <path d={mouth} stroke="#38274B" strokeWidth="3.5" fill="none" strokeLinecap="round"/>}
        <ellipse cx="65" cy="106" rx="8" ry="4" fill="white" opacity=".3"/><ellipse cx="135" cy="106" rx="8" ry="4" fill="white" opacity=".3"/>
      </g>
      {state === 'working' && <g className="working-ring" stroke={paint} fill="none" strokeWidth="3" strokeLinecap="round"><circle cx="100" cy="100" r="92" strokeDasharray="55 25 12 45"/></g>}
      {state === 'error' && <g><circle cx="163" cy="159" r="17" fill="#fff" stroke="#B42342" strokeWidth="2"/><path d="M163 150v10m0 6h.1" stroke="#B42342" strokeWidth="3" strokeLinecap="round"/></g>}
    </svg>
    {state === 'speaking' && <div className="fixture-wave"><i/><i/><i/><i/><i/></div>}
  </div>;
}
