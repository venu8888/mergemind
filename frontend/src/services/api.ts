import type {
  CIFailure,
  HealthTimelinePoint,
  PatchVerification,
  RemediationProposal,
  RemediationPullRequest,
  Repository,
  RepositoryDashboard,
  RepositoryHealth,
  SystemHealth,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || 'mergemind-dev-insecure-key';

export function getApiKey(): string {
  return localStorage.getItem('mergemind_api_key') || DEFAULT_API_KEY;
}

export function setApiKey(key: string): void {
  localStorage.setItem('mergemind_api_key', key);
}

async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers || {});
  const key = getApiKey();
  if (key && !headers.has('X-API-Key')) {
    headers.set('X-API-Key', key);
  }
  return fetch(input, { ...init, headers });
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // fallback to statusText
    }
    throw new Error(`API Error [${res.status}]: ${errorDetail}`);
  }
  return res.json();
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/health`);
  return handleResponse<SystemHealth>(res);
}

export async function fetchRepositories(): Promise<Repository[]> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories`);
  return handleResponse<Repository[]>(res);
}

export async function fetchRepositoryDashboard(repoId: string): Promise<RepositoryDashboard> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/dashboard`);
  return handleResponse<RepositoryDashboard>(res);
}

export async function fetchRepositoryHealth(repoId: string): Promise<RepositoryHealth> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/health`);
  return handleResponse<RepositoryHealth>(res);
}

export async function triggerHealthAssessment(
  repoId: string,
  branch: string = 'main'
): Promise<RepositoryHealth> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/health/assess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ branch }),
  });
  return handleResponse<RepositoryHealth>(res);
}

export async function fetchHealthHistory(repoId: string): Promise<HealthTimelinePoint[]> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/health/history`);
  return handleResponse<HealthTimelinePoint[]>(res);
}

export async function fetchCIFailures(repoId: string): Promise<CIFailure[]> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/ci-failures`);
  return handleResponse<CIFailure[]>(res);
}

export async function fetchCIFailureDetail(
  repoId: string,
  failureId: string
): Promise<CIFailure> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/ci-failures/${failureId}`);
  return handleResponse<CIFailure>(res);
}

export async function ingestCIFailure(payload: {
  repository_id: string;
  workflow_name: string;
  commit_sha: string;
  raw_log: string;
  job_name?: string;
  workflow_run_id?: number;
}): Promise<CIFailure> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/ci-failures/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<CIFailure>(res);
}

export async function fetchRemediationProposals(repoId: string): Promise<RemediationProposal[]> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/remediations`);
  return handleResponse<RemediationProposal[]>(res);
}

export async function proposeRemediation(payload: {
  ci_failure_id?: string;
  finding_id?: string;
}): Promise<RemediationProposal> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/remediations/propose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<RemediationProposal>(res);
}

export const generateRemediationProposal = (failureId: string) =>
  proposeRemediation({ ci_failure_id: failureId });

export async function verifyRemediationPatch(
  proposalId: string
): Promise<PatchVerification> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/remediations/${proposalId}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  return handleResponse<PatchVerification>(res);
}

export const verifyRemediationProposal = verifyRemediationPatch;

export async function createCorrectivePR(
  proposalId: string,
  baseBranch?: string
): Promise<RemediationPullRequest> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/remediations/${proposalId}/create-pr`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_branch: baseBranch }),
  });
  return handleResponse<RemediationPullRequest>(res);
}

export const createRemediationPullRequest = (proposalId: string, baseBranch?: string) =>
  createCorrectivePR(proposalId, baseBranch);

export async function postMergeReassess(
  repoId: string,
  commitSha: string,
  branch: string = 'main'
): Promise<RepositoryHealth> {
  const url = `${API_BASE_URL}/api/v1/repositories/${repoId}/remediation/post-merge-reassess?commit_sha=${encodeURIComponent(
    commitSha
  )}&branch=${encodeURIComponent(branch)}`;
  const res = await authFetch(url, { method: 'POST' });
  return handleResponse<RepositoryHealth>(res);
}

// ==============================================================================
// Codebase Explorer, Intelligence & Live GitHub Pull Request APIs
// ==============================================================================

export async function fetchRepositoryTree(
  repoId: string,
  branch: string = 'main'
): Promise<{ repository: string; branch: string; tree: Array<{ path: string; type: string; size?: number; sha: string }> }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/tree?branch=${encodeURIComponent(branch)}`);
  return handleResponse(res);
}

export async function fetchRepositoryBlob(
  repoId: string,
  path: string,
  ref: string = 'main'
): Promise<{ path: string; content: string; size: number; lines: number; language: string }> {
  const res = await authFetch(
    `${API_BASE_URL}/api/v1/repositories/${repoId}/blob?path=${encodeURIComponent(path)}&ref=${encodeURIComponent(ref)}`
  );
  return handleResponse(res);
}

export async function fetchRepositoryBranches(
  repoId: string
): Promise<Array<{ name: string; commit_sha: string; protected: boolean }>> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/branches`);
  return handleResponse(res);
}

export async function fetchRepositoryCommits(
  repoId: string,
  limit: number = 15
): Promise<Array<{ sha: string; short_sha: string; message: string; author: string; date: string; html_url?: string }>> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/commits?limit=${limit}`);
  return handleResponse(res);
}

export async function fetchRepositoryIntelligence(
  repoId: string,
  branch: string = 'main'
): Promise<{
  repository: string;
  branch: string;
  total_files: number;
  python_files_count: number;
  test_files_count: number;
  doc_files_count: number;
  total_loc: number;
  technologies: string[];
  avg_complexity: number;
  complex_functions_count: number;
  function_complexities: Array<{ file: string; function: string; line: number; complexity: number; grade: string }>;
  modules: Array<{ path: string; loc: number; imports: string[] }>;
  ai_insights: {
    architecture_pattern: string;
    modularity_score: number;
    strengths: string[];
    risks: string[];
    recommendations: string[];
    confidence: number;
  };
}> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/intelligence?branch=${encodeURIComponent(branch)}`);
  return handleResponse(res);
}

export async function fetchGitHubPullRequests(
  repoId: string,
  state: string = 'all'
): Promise<Array<{
  number: number;
  title: string;
  state: string;
  draft: boolean;
  author: string;
  author_avatar?: string;
  created_at: string;
  head_branch: string;
  head_sha: string;
  base_branch: string;
  html_url: string;
  body: string;
}>> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/github-pulls?state=${encodeURIComponent(state)}`);
  return handleResponse(res);
}

export async function fetchGitHubPullRequestDetail(
  repoId: string,
  pullNumber: number
): Promise<{
  number: number;
  title: string;
  state: string;
  draft: boolean;
  author: string;
  author_avatar?: string;
  created_at: string;
  head_branch: string;
  head_sha: string;
  base_branch: string;
  html_url: string;
  body: string;
  changed_files: Array<{ filename: string; status: string; additions: number; deletions: number; changes: number; patch?: string }>;
  diff: string;
  additions: number;
  deletions: number;
}> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/github-pulls/${pullNumber}`);
  return handleResponse(res);
}

export async function reviewPullRequestWithAI(
  repoId: string,
  pullNumber: number
): Promise<{
  summary: string;
  quality_gate: string;
  risk_level: string;
  verdict: string;
  findings: Array<{ category: string; file: string; line: number; message: string; recommendation: string }>;
  positive_observations: string[];
  provider: string;
  reviewed_at?: string;
}> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/github-pulls/${pullNumber}/review`, {
    method: 'POST',
  });
  return handleResponse(res);
}

export async function verifyPullRequestInSandbox(
  repoId: string,
  pullNumber: number
): Promise<{
  pr_number: number;
  verification_status: string;
  tests_passed: number;
  tests_failed: number;
  pass_rate_pct: number;
  quality_gate: string;
  duration_ms: number;
  summary: string;
}> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/github-pulls/${pullNumber}/verify`, {
    method: 'POST',
  });
  return handleResponse(res);
}
