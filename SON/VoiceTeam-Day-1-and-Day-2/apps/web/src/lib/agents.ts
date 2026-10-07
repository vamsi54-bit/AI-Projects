export type PreviewState = 'idle' | 'working' | 'speaking' | 'error';
export type AgentState = PreviewState | 'unavailable';
export type AgentId = 'supervisor' | 'researcher' | 'solver' | 'verifier';
export const previewStates: PreviewState[] = ['idle', 'working', 'speaking', 'error'];
export const agents = [
  { id: 'supervisor', name: 'Supervisor', role: 'Conversation & coordination', detail: 'One place to bring it all together.', from: '#8B5CF6', to: '#EC4899', gradient: 'bg-linear-to-br from-[#8B5CF6] to-[#EC4899]', icon: 'spark' },
  { id: 'researcher', name: 'Researcher', role: 'Sources & evidence', detail: 'A curious eye for useful context.', from: '#06B6D4', to: '#3B82F6', gradient: 'bg-linear-to-br from-[#06B6D4] to-[#3B82F6]', icon: 'search' },
  { id: 'solver', name: 'Problem Solver', role: 'Ideas & explanations', detail: 'A little spark of clarity.', from: '#F43F5E', to: '#F59E0B', gradient: 'bg-linear-to-br from-[#F43F5E] to-[#F59E0B]', icon: 'solve' },
  { id: 'verifier', name: 'Verifier', role: 'Claims & coverage', detail: 'A calm second look.', from: '#10B981', to: '#84CC16', gradient: 'bg-linear-to-br from-[#10B981] to-[#84CC16]', icon: 'shield' },
] as const;
export type AgentProfile = typeof agents[number];
