import type { ReactNode } from 'react';
type IconName = 'spark' | 'search' | 'solve' | 'shield' | 'mic' | 'attach' | 'arrow' | 'sound' | 'chat';
export function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
 const paths: Record<IconName, ReactNode> = {
  spark: <><path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z"/><path d="m20 2 .5 1.5L22 4l-1.5.5L20 6l-.5-1.5L18 4l1.5-.5Z"/></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
  solve: <><path d="m14 2-9 12h7l-2 8 9-12h-7Z"/></>,
  shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/></>,
  mic: <><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/></>,
  attach: <path d="m9 12 6-6a3 3 0 0 1 4 4l-9 9a5 5 0 0 1-7-7l9-9m-5 12 8-8"/>,
  arrow: <><path d="M4 12h16m-6-6 6 6-6 6"/></>,
  sound: <><path d="m11 4-6 5H2v6h3l6 5Zm4 4a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/></>,
  chat: <path d="M20 11a8 8 0 0 1-8 8H4l-3 3V11a9 9 0 0 1 19 0Z"/>,
 };
 return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
