export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'error' | 'pending' | string;
  version: string;
  environment: string;
  database: {
    connected: boolean;
    url_driver?: string;
  } | any;
  sandbox?: {
    mode: string;
    timeout_seconds: number;
    max_memory_mb: number;
  };
  timestamp: string;
}

export interface Repository {
  id: string;
  github_repo_id: number;
  full_name: string;
  name?: string;
  default_branch: string;
  is_active: boolean;
  registered_at: string;
}

export interface DimensionScore {
  score: number;
  weight: number;
  status?: string;
  availability?: string;
  available?: boolean;
  findings_summary?: any;
}

export interface DimensionStatus {
  code_quality?: string;
  security?: string;
  dependencies?: string;
  test_health?: string;
  maintainability?: string;
  [key: string]: string | undefined;
}

export interface RepositoryHealth {
  id: string;
  repository_id: string;
  commit_sha?: string;
  branch_name?: string;
  health_score: number;
  assessment_completeness: number;
  check_availability?: number;
  is_qualified?: boolean;
  qualification_status?: string;
  qualification_reason?: string | null;
  code_quality_score?: number | null;
  security_score?: number | null;
  dependency_score?: number | null;
  test_health_score?: number | null;
  maintainability_score?: number | null;
  scoring_policy_version?: string;
  dimension_status?: DimensionStatus;
  breakdown?: Record<string, DimensionScore>;
  summary_metrics?: Record<string, any>;
  status?: string;
  created_at: string;
}

export type RepositoryHealthAssessment = RepositoryHealth;

export interface HealthTimelinePoint {
  id: string;
  commit_sha: string;
  branch_name: string;
  health_score: number | null;
  assessment_completeness: number;
  is_qualified: boolean;
  qualification_status?: string;
  code_quality_score?: number | null;
  security_score?: number | null;
  dependency_score?: number | null;
  test_health_score?: number | null;
  maintainability_score?: number | null;
  created_at: string;
}

export interface LocalizedFile {
  file_path?: string;
  path?: string;
  file?: string;
  line_number?: number;
  line?: number;
  function?: string;
  enclosing_symbol?: string | null;
  context?: string;
}

export interface RootCauseAnalysis {
  category: string;
  primary_error: string;
  primary_file?: string | null;
  primary_line?: number | null;
  enclosing_symbol?: string | null;
  direct_match_with_diff?: boolean;
  all_extracted_locations?: LocalizedFile[];
}

export interface CIFailure {
  id: string;
  repository_id: string;
  pull_request_id?: string | null;
  workflow_run_id?: number;
  workflow_name: string;
  job_id?: number | null;
  job_name?: string;
  commit_sha: string;
  branch?: string;
  failure_category?: string;
  classification?: string;
  confidence?: number;
  status: string;
  error_message?: string;
  error_summary?: string;
  log_excerpt?: string;
  raw_log?: string;
  sanitized_log?: string;
  stack_locations?: LocalizedFile[] | any[];
  localized_files?: LocalizedFile[];
  root_cause_analysis?: RootCauseAnalysis;
  root_cause_hypothesis?: string | null;
  ai_advisory_hypothesis?: string | null;
  created_at: string;
  updated_at?: string;
}

export type CIFailureRecord = CIFailure;
export type CIFailureClassification = string;

export interface PatchVerification {
  id: string;
  proposal_id?: string;
  sandbox_status?: string;
  verification_status: 'VERIFIED' | 'REGRESSION_INTRODUCED' | 'UNRESOLVED' | 'TIMEOUT' | 'ERROR' | string;
  is_verified?: boolean;
  baseline_passed?: boolean;
  patched_passed?: boolean;
  regressions_detected?: boolean;
  regressions_count?: number;
  resolved_issues_count?: number;
  pre_patch_findings_count?: number;
  post_patch_findings_count?: number;
  pre_patch_findings?: any[];
  post_patch_findings?: any[];
  test_results?: Record<string, any>;
  sandbox_logs?: string;
  execution_log?: string;
  duration_ms?: number;
  created_at: string;
}

export interface RemediationPullRequest {
  id: string;
  proposal_id?: string;
  remediation_proposal_id?: string;
  repository_id: string;
  pr_number?: number;
  github_pr_number?: number;
  branch_name: string;
  base_branch: string;
  pr_url?: string;
  html_url?: string;
  status: string;
  merged_at?: string | null;
  created_at: string;
}

export interface RemediationProposal {
  id: string;
  repository_id: string;
  ci_failure_id?: string | null;
  finding_id?: string | null;
  pull_request_id?: string | null;
  title?: string;
  description?: string;
  explanation?: string;
  rationale?: string;
  target_commit_sha?: string;
  target_branch?: string;
  status: string;
  risk_level?: string;
  remediation_strategy?: string;
  provider_name?: string;
  model_identifier?: string | null;
  confidence_score: number;
  patch_diff: string;
  affected_files?: string[];
  evidence_records?: Record<string, any>;
  verification?: PatchVerification | null;
  verifications?: PatchVerification[];
  pull_request?: RemediationPullRequest | null;
  remediation_pr?: RemediationPullRequest | null;
  created_at: string;
  updated_at?: string;
}

export interface ActionableRecommendation {
  category: string;
  title: string;
  severity: string;
  description: string;
  target_file?: string | null;
  line_number?: number | null;
  remediation_proposal_id?: string | null;
  evidence_id?: string | null;
}

export interface RepositoryDashboard {
  repository: Repository;
  current_health?: RepositoryHealth | null;
  latest_health?: RepositoryHealth | null;
  health_history: (HealthTimelinePoint | RepositoryHealth)[];
  open_ci_failures: CIFailure[];
  active_remediations: RemediationProposal[];
  actionable_recommendations?: ActionableRecommendation[];
  summary_counts?: {
    open_ci_failures?: number;
    active_remediations?: number;
    total_historical_assessments?: number;
  };
}
