// ==============================================================================
// Project ARGUS-INT - Mock Data for Frontend Development
// ==============================================================================

export interface GraphNode {
  id: string;
  label: string;
  type: 'email' | 'username' | 'ip' | 'domain' | 'wallet' | 'person' | 'service' | 'phone';
  data: Record<string, string | number | boolean>;
  investigation_id?: string;
  first_seen?: string;
  last_seen?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  confidence: number;
  data?: Record<string, string | number>;
  first_seen?: string;
}

export interface Investigation {
  id: string;
  target: string;
  target_type: string;
  depth: number;
  status: 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED';
  created_at: string;
  completed_at?: string;
  result_count: number;
  modules_used: string[];
}

export interface WorkerInfo {
  name: string;
  queue: string;
  status: 'online' | 'offline' | 'busy';
  tasks_completed: number;
  tasks_failed: number;
  avg_time_ms: number;
}

// ── Mock Investigations ─────────────────────────────────────────

export const mockInvestigations: Investigation[] = [
  {
    id: 'inv-a1b2c3',
    target: 'ghost.operator@proton.me',
    target_type: 'email',
    depth: 3,
    status: 'DONE',
    created_at: '2026-05-20T14:32:00Z',
    completed_at: '2026-05-20T14:38:22Z',
    result_count: 47,
    modules_used: ['identity', 'breach', 'darkweb', 'crypto_trace'],
  },
  {
    id: 'inv-d4e5f6',
    target: 'shadow_phoenix',
    target_type: 'username',
    depth: 2,
    status: 'RUNNING',
    created_at: '2026-05-22T09:15:00Z',
    result_count: 12,
    modules_used: ['identity', 'breach', 'stylometry'],
  },
  {
    id: 'inv-g7h8i9',
    target: '185.220.101.42',
    target_type: 'ip',
    depth: 1,
    status: 'DONE',
    created_at: '2026-05-19T22:10:00Z',
    completed_at: '2026-05-19T22:12:45Z',
    result_count: 8,
    modules_used: ['techrecon', 'geoint'],
  },
  {
    id: 'inv-j0k1l2',
    target: 'darkmarket.onion',
    target_type: 'domain',
    depth: 2,
    status: 'FAILED',
    created_at: '2026-05-18T03:00:00Z',
    result_count: 0,
    modules_used: ['darkweb'],
  },
  {
    id: 'inv-m3n4o5',
    target: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
    target_type: 'wallet',
    depth: 3,
    status: 'PENDING',
    created_at: '2026-05-22T11:00:00Z',
    result_count: 0,
    modules_used: ['crypto_trace', 'finops'],
  },
];

// ── Mock Graph Data ─────────────────────────────────────────────

export const mockNodes: GraphNode[] = [
  { id: 'n1', label: 'ghost.operator@proton.me', type: 'email', data: { provider: 'ProtonMail', verified: true }, first_seen: '2026-05-20T14:32:00Z', last_seen: '2026-05-20T14:38:00Z' },
  { id: 'n2', label: 'shadow_phoenix', type: 'username', data: { platform_count: 7 }, first_seen: '2026-05-20T14:33:00Z', last_seen: '2026-05-20T14:36:00Z' },
  { id: 'n3', label: 'ghost_op', type: 'username', data: { platform_count: 3 }, first_seen: '2026-05-20T14:33:30Z' },
  { id: 'n4', label: 'GitHub:shadow_phoenix', type: 'service', data: { service: 'GitHub', followers: 234 }, first_seen: '2026-05-20T14:33:00Z' },
  { id: 'n5', label: 'Twitter:ghost_op', type: 'service', data: { service: 'Twitter', followers: 1200 }, first_seen: '2026-05-20T14:33:30Z' },
  { id: 'n6', label: 'Telegram:shadowphx', type: 'service', data: { service: 'Telegram' }, first_seen: '2026-05-20T14:34:00Z' },
  { id: 'n7', label: '185.220.101.42', type: 'ip', data: { country: 'DE', asn: 'AS205100', tor_exit: true }, first_seen: '2026-05-20T14:34:30Z' },
  { id: 'n8', label: '91.132.147.168', type: 'ip', data: { country: 'NL', asn: 'AS49981' }, first_seen: '2026-05-20T14:34:30Z' },
  { id: 'n9', label: 'shadow-tools.io', type: 'domain', data: { registrar: 'Njalla', created: '2024-01-15' }, first_seen: '2026-05-20T14:35:00Z' },
  { id: 'n10', label: 'darkmarket.onion', type: 'domain', data: { onion: true }, first_seen: '2026-05-20T14:35:00Z' },
  { id: 'n11', label: 'bc1qxy2kg...x0wlh', type: 'wallet', data: { chain: 'BTC', balance_sat: 4200000 }, first_seen: '2026-05-20T14:35:30Z' },
  { id: 'n12', label: '0x742d35Cc...8C2d', type: 'wallet', data: { chain: 'ETH', balance_wei: '1500000000000000000' }, first_seen: '2026-05-20T14:35:30Z' },
  { id: 'n13', label: '47tKBx...8zGk', type: 'wallet', data: { chain: 'XMR' }, first_seen: '2026-05-20T14:36:00Z' },
  { id: 'n14', label: '+49 176 ***4821', type: 'phone', data: { country: 'DE', carrier: 'O2' }, first_seen: '2026-05-20T14:36:00Z' },
  { id: 'n15', label: 'John D.', type: 'person', data: { confidence: 0.72, aliases: 3 }, first_seen: '2026-05-20T14:36:30Z' },
  { id: 'n16', label: 'Discord:darkphx#1337', type: 'service', data: { service: 'Discord' }, first_seen: '2026-05-20T14:34:00Z' },
  { id: 'n17', label: 'Reddit:u/sh4dow_op', type: 'service', data: { service: 'Reddit', karma: 15400 }, first_seen: '2026-05-20T14:34:15Z' },
  { id: 'n18', label: 'darktools.dev', type: 'domain', data: { registrar: 'Cloudflare' }, first_seen: '2026-05-20T14:35:00Z' },
  { id: 'n19', label: 'keybase:ghostop', type: 'service', data: { service: 'Keybase', pgp: true }, first_seen: '2026-05-20T14:34:30Z' },
  { id: 'n20', label: 'ghost.operator@tutanota.com', type: 'email', data: { provider: 'Tutanota' }, first_seen: '2026-05-20T14:37:00Z' },
  { id: 'n21', label: 'tor-relay-de01', type: 'ip', data: { country: 'DE', tor_relay: true, bandwidth_mbps: 50 }, first_seen: '2026-05-20T14:37:00Z' },
  { id: 'n22', label: 'breached-db:Collection#3', type: 'service', data: { service: 'LeakDB', records: 2 }, first_seen: '2026-05-20T14:37:30Z' },
  { id: 'n23', label: 'Matrix:@ghost:matrix.org', type: 'service', data: { service: 'Matrix' }, first_seen: '2026-05-20T14:34:45Z' },
  { id: 'n24', label: 'Mastodon:@shadow@infosec.exchange', type: 'service', data: { service: 'Mastodon', toots: 342 }, first_seen: '2026-05-20T14:35:15Z' },
];

export const mockEdges: GraphEdge[] = [
  { source: 'n1', target: 'n2', type: 'ALIAS_OF', confidence: 0.92, first_seen: '2026-05-20T14:33:00Z' },
  { source: 'n1', target: 'n3', type: 'ALIAS_OF', confidence: 0.85, first_seen: '2026-05-20T14:33:30Z' },
  { source: 'n2', target: 'n4', type: 'HAS_PROFILE', confidence: 0.99, first_seen: '2026-05-20T14:33:00Z' },
  { source: 'n3', target: 'n5', type: 'HAS_PROFILE', confidence: 0.95, first_seen: '2026-05-20T14:33:30Z' },
  { source: 'n2', target: 'n6', type: 'HAS_PROFILE', confidence: 0.88, first_seen: '2026-05-20T14:34:00Z' },
  { source: 'n2', target: 'n16', type: 'HAS_PROFILE', confidence: 0.91, first_seen: '2026-05-20T14:34:00Z' },
  { source: 'n2', target: 'n17', type: 'HAS_PROFILE', confidence: 0.87, first_seen: '2026-05-20T14:34:15Z' },
  { source: 'n1', target: 'n19', type: 'HAS_PROFILE', confidence: 0.94, first_seen: '2026-05-20T14:34:30Z' },
  { source: 'n2', target: 'n23', type: 'HAS_PROFILE', confidence: 0.82, first_seen: '2026-05-20T14:34:45Z' },
  { source: 'n2', target: 'n24', type: 'HAS_PROFILE', confidence: 0.79, first_seen: '2026-05-20T14:35:15Z' },
  { source: 'n5', target: 'n7', type: 'LOGGED_FROM', confidence: 0.67, first_seen: '2026-05-20T14:34:30Z' },
  { source: 'n4', target: 'n8', type: 'LOGGED_FROM', confidence: 0.73, first_seen: '2026-05-20T14:34:30Z' },
  { source: 'n7', target: 'n9', type: 'RESOLVES_TO', confidence: 0.95, first_seen: '2026-05-20T14:35:00Z' },
  { source: 'n8', target: 'n18', type: 'RESOLVES_TO', confidence: 0.90, first_seen: '2026-05-20T14:35:00Z' },
  { source: 'n6', target: 'n10', type: 'POSTED_ON', confidence: 0.78, first_seen: '2026-05-20T14:35:00Z' },
  { source: 'n1', target: 'n11', type: 'OWNS_WALLET', confidence: 0.65, first_seen: '2026-05-20T14:35:30Z' },
  { source: 'n2', target: 'n12', type: 'OWNS_WALLET', confidence: 0.58, first_seen: '2026-05-20T14:35:30Z' },
  { source: 'n11', target: 'n13', type: 'TRANSACTED_WITH', confidence: 0.45, first_seen: '2026-05-20T14:36:00Z' },
  { source: 'n1', target: 'n14', type: 'PHONE_LINKED', confidence: 0.71, first_seen: '2026-05-20T14:36:00Z' },
  { source: 'n15', target: 'n1', type: 'IDENTIFIED_AS', confidence: 0.72, first_seen: '2026-05-20T14:36:30Z' },
  { source: 'n15', target: 'n14', type: 'PHONE_LINKED', confidence: 0.80, first_seen: '2026-05-20T14:36:30Z' },
  { source: 'n1', target: 'n20', type: 'ALIAS_OF', confidence: 0.88, first_seen: '2026-05-20T14:37:00Z' },
  { source: 'n7', target: 'n21', type: 'RELAY_CHAIN', confidence: 0.60, first_seen: '2026-05-20T14:37:00Z' },
  { source: 'n1', target: 'n22', type: 'FOUND_IN_BREACH', confidence: 0.99, first_seen: '2026-05-20T14:37:30Z' },
  { source: 'n20', target: 'n22', type: 'FOUND_IN_BREACH', confidence: 0.99, first_seen: '2026-05-20T14:37:30Z' },
  { source: 'n9', target: 'n18', type: 'LINKED_DOMAIN', confidence: 0.82, first_seen: '2026-05-20T14:35:00Z' },
];

// ── Mock Workers ────────────────────────────────────────────────

export const mockWorkers: WorkerInfo[] = [
  { name: 'worker-identity', queue: 'identity', status: 'online', tasks_completed: 342, tasks_failed: 3, avg_time_ms: 4200 },
  { name: 'worker-breach', queue: 'breach', status: 'online', tasks_completed: 189, tasks_failed: 12, avg_time_ms: 8500 },
  { name: 'worker-darkweb', queue: 'darkweb', status: 'busy', tasks_completed: 87, tasks_failed: 24, avg_time_ms: 32000 },
  { name: 'worker-geoint', queue: 'geoint', status: 'offline', tasks_completed: 45, tasks_failed: 2, avg_time_ms: 15000 },
  { name: 'worker-techrecon', queue: 'techrecon', status: 'online', tasks_completed: 256, tasks_failed: 8, avg_time_ms: 6100 },
  { name: 'worker-finops', queue: 'finops', status: 'online', tasks_completed: 23, tasks_failed: 1, avg_time_ms: 45000 },
  { name: 'worker-stylometry', queue: 'stylometry', status: 'offline', tasks_completed: 12, tasks_failed: 0, avg_time_ms: 28000 },
];

// ── Stats ───────────────────────────────────────────────────────

export const mockStats = {
  activeInvestigations: 2,
  totalEntities: 24,
  totalRelations: 25,
  workersOnline: 5,
};
