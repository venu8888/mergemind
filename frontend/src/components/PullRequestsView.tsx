import React, { useState, useEffect } from 'react';
import {
  GitPullRequest,
  CheckCircle2,
  Play,
  Sparkles,
  ExternalLink,
  RotateCw,
  FileDiff,
  FileCode,
  Check,
  Copy,
  User,
  ArrowRight,
} from 'lucide-react';
import {
  fetchGitHubPullRequests,
  fetchGitHubPullRequestDetail,
  reviewPullRequestWithAI,
  verifyPullRequestInSandbox,
} from '../services/api';

interface PullRequestsViewProps {
  repositoryId: string;
}

export const PullRequestsView: React.FC<PullRequestsViewProps> = ({ repositoryId }) => {
  const [prs, setPrs] = useState<any[]>([]);
  const [filterState, setFilterState] = useState<'all' | 'open' | 'closed'>('all');
  const [selectedPrNumber, setSelectedPrNumber] = useState<number | null>(null);
  const [prDetail, setPrDetail] = useState<any | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [isReviewing, setIsReviewing] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [reviewResult, setReviewResult] = useState<any | null>(null);
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'diff' | 'files' | 'review'>('diff');
  const [copiedDiff, setCopiedDiff] = useState<boolean>(false);

  // Load PR list
  const loadPrList = async () => {
    if (!repositoryId) return;
    setLoadingList(true);
    try {
      const list = await fetchGitHubPullRequests(repositoryId, filterState);
      setPrs(list);
      if (list.length > 0 && !selectedPrNumber) {
        setSelectedPrNumber(list[0].number);
      }
    } catch (err) {
      console.error('Failed to load GitHub PRs:', err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadPrList();
  }, [repositoryId, filterState]);

  // Load PR detail when selected
  useEffect(() => {
    if (!repositoryId || !selectedPrNumber) return;
    const loadDetail = async () => {
      setLoadingDetail(true);
      setReviewResult(null);
      setVerificationResult(null);
      try {
        const detail = await fetchGitHubPullRequestDetail(repositoryId, selectedPrNumber);
        setPrDetail(detail);
      } catch (err) {
        console.error('Failed to load PR detail:', err);
      } finally {
        setLoadingDetail(false);
      }
    };
    loadDetail();
  }, [repositoryId, selectedPrNumber]);

  // AI PR Review action
  const handleRunAIReview = async () => {
    if (!repositoryId || !selectedPrNumber) return;
    setIsReviewing(true);
    try {
      const review = await reviewPullRequestWithAI(repositoryId, selectedPrNumber);
      setReviewResult(review);
      setActiveTab('review');
    } catch (err: any) {
      alert('AI PR Review failed: ' + (err.message || 'Error communicating with Gemini'));
    } finally {
      setIsReviewing(false);
    }
  };

  // Sandbox Verification action
  const handleVerifySandbox = async () => {
    if (!repositoryId || !selectedPrNumber) return;
    setIsVerifying(true);
    try {
      const result = await verifyPullRequestInSandbox(repositoryId, selectedPrNumber);
      setVerificationResult(result);
    } catch (err: any) {
      alert('Sandbox verification failed: ' + (err.message || 'Error running pytest sandbox'));
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCopyDiff = (diffText: string) => {
    navigator.clipboard.writeText(diffText);
    setCopiedDiff(true);
    setTimeout(() => setCopiedDiff(false), 2000);
  };

  const renderUnifiedDiff = (diffText: string) => {
    if (!diffText || !diffText.trim()) {
      return (
        <div className="p-8 text-center text-slate-500 font-mono text-xs">
          No diff changes recorded for this Pull Request.
        </div>
      );
    }
    const lines = diffText.split('\n');
    return (
      <div className="font-mono text-xs overflow-x-auto p-4 bg-slate-950 rounded-lg border border-slate-800 max-h-[500px] leading-relaxed select-text">
        {lines.map((line, idx) => {
          let lineClass = 'text-slate-300';
          if (line.startsWith('+') && !line.startsWith('+++')) {
            lineClass = 'bg-emerald-950/60 text-emerald-300 font-medium px-1';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            lineClass = 'bg-rose-950/60 text-rose-300 font-medium px-1';
          } else if (line.startsWith('@@')) {
            lineClass = 'text-cyan-400 font-semibold my-1';
          } else if (line.startsWith('diff --git') || line.startsWith('index ')) {
            lineClass = 'text-slate-500 font-bold';
          }

          return (
            <div key={idx} className={`${lineClass} whitespace-pre`}>
              {line || ' '}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <GitPullRequest className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Pull Request Intelligence & Review</h2>
            <p className="text-xs text-slate-400">
              Real GitHub PR tracking, deterministic sandbox quality gates, and automated AI code review.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* State Filter Buttons */}
          <div className="flex items-center bg-slate-800 p-1 rounded-lg text-xs font-medium border border-slate-700">
            {(['all', 'open', 'closed'] as const).map((st) => (
              <button
                key={st}
                onClick={() => setFilterState(st)}
                className={`px-3 py-1 rounded capitalize transition ${
                  filterState === st ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={loadPrList}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition border border-slate-700"
            title="Refresh Pull Requests"
          >
            <RotateCw className={`w-4 h-4 ${loadingList ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: PR Listing */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            Pull Requests ({prs.length})
          </div>

          <div className="space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
            {prs.length > 0 ? (
              prs.map((pr) => {
                const isSelected = pr.number === selectedPrNumber;
                return (
                  <div
                    key={pr.number}
                    onClick={() => setSelectedPrNumber(pr.number)}
                    className={`p-4 rounded-xl cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-950/30'
                        : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="text-sm font-semibold text-white truncate">
                        #{pr.number} {pr.title}
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                          pr.state === 'open'
                            ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                            : 'bg-purple-950 text-purple-400 border-purple-800'
                        }`}
                      >
                        {pr.draft ? 'DRAFT' : pr.state}
                      </span>
                    </div>

                    <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5 mb-2">
                      <span className="text-slate-300 font-semibold">{pr.head_branch}</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="text-slate-500">{pr.base_branch}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <div className="flex items-center gap-1.5">
                        {pr.author_avatar ? (
                          <img src={pr.author_avatar} alt="" className="w-4 h-4 rounded-full" />
                        ) : (
                          <User className="w-3.5 h-3.5" />
                        )}
                        <span>{pr.author}</span>
                      </div>
                      <span>{new Date(pr.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-500 text-sm">
                No pull requests match filter '{filterState}'.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Detailed PR Console */}
        <div className="lg:col-span-8">
          {loadingDetail ? (
            <div className="h-full min-h-[400px] flex items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl text-slate-400 text-xs gap-2">
              <RotateCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Fetching Pull Request details and diff from GitHub...</span>
            </div>
          ) : prDetail ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              {/* PR Header & Actions */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-slate-800">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-white">
                      #{prDetail.number} {prDetail.title}
                    </span>
                    <a
                      href={prDetail.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-indigo-400 transition"
                      title="Open on GitHub"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                  <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
                    <span>Author: {prDetail.author}</span>
                    <span>•</span>
                    <span>Branch: {prDetail.head_branch} &rarr; {prDetail.base_branch}</span>
                    <span>•</span>
                    <span className="text-emerald-400">+{prDetail.additions}</span>
                    <span className="text-rose-400">-{prDetail.deletions}</span>
                  </div>
                </div>

                {/* Verification & AI Review Triggers */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={handleVerifySandbox}
                    disabled={isVerifying}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white text-xs font-medium transition shadow-md shadow-emerald-950/20"
                  >
                    {isVerifying ? (
                      <>
                        <RotateCw className="w-3.5 h-3.5 animate-spin" />
                        Verifying...
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        Verify in Sandbox
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleRunAIReview}
                    disabled={isReviewing}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-medium transition shadow-md shadow-indigo-950/20"
                  >
                    {isReviewing ? (
                      <>
                        <RotateCw className="w-3.5 h-3.5 animate-spin" />
                        Reviewing with AI...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        Run AI Review
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Sandbox Verification Result Card (if verified) */}
              {verificationResult && (
                <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/60 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-emerald-400 font-bold">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Deterministic Sandbox Quality Gate: {verificationResult.quality_gate}</span>
                    </div>
                    <span className="font-mono text-slate-400">{verificationResult.duration_ms}ms</span>
                  </div>
                  <p className="text-slate-300">{verificationResult.summary}</p>
                </div>
              )}

              {/* View Sub-Tabs */}
              <div className="flex items-center space-x-1 border-b border-slate-800">
                <button
                  onClick={() => setActiveTab('diff')}
                  className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition ${
                    activeTab === 'diff'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileDiff className="w-3.5 h-3.5" />
                  <span>Unified Patch Diff</span>
                </button>

                <button
                  onClick={() => setActiveTab('files')}
                  className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition ${
                    activeTab === 'files'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>Changed Files ({prDetail.changed_files.length})</span>
                </button>

                <button
                  onClick={() => setActiveTab('review')}
                  className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition ${
                    activeTab === 'review'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Review Verdict {reviewResult && `(${reviewResult.verdict})`}</span>
                </button>
              </div>

              {/* Tab 1: Diff Viewer */}
              {activeTab === 'diff' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                    <span>Unified Git Diff</span>
                    <button
                      onClick={() => handleCopyDiff(prDetail.diff)}
                      className="inline-flex items-center gap-1 hover:text-white"
                    >
                      {copiedDiff ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedDiff ? 'Copied' : 'Copy Diff'}</span>
                    </button>
                  </div>
                  {renderUnifiedDiff(prDetail.diff)}
                </div>
              )}

              {/* Tab 2: Changed Files */}
              {activeTab === 'files' && (
                <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                  {prDetail.changed_files.map((f: any) => (
                    <div
                      key={f.filename}
                      className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-emerald-400" />
                        <span className="text-white font-medium">{f.filename}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold bg-slate-800 text-slate-400">
                          {f.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-emerald-400">+{f.additions}</span>
                        <span className="text-rose-400">-{f.deletions}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 3: Gemini AI Review Results */}
              {activeTab === 'review' && (
                <div className="space-y-4">
                  {reviewResult ? (
                    <div className="space-y-4">
                      {/* Summary Banner */}
                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider border ${
                                reviewResult.verdict === 'APPROVE'
                                  ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                                  : 'bg-amber-950 text-amber-300 border-amber-800'
                              }`}
                            >
                              {reviewResult.verdict}
                            </span>
                            <span className="text-xs font-mono text-slate-400">
                              Gate: {reviewResult.quality_gate} • Risk: {reviewResult.risk_level}
                            </span>
                          </div>
                          <span className="text-xs font-mono text-indigo-400">
                            Provider: {reviewResult.provider}
                          </span>
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed">{reviewResult.summary}</p>
                      </div>

                      {/* Findings List */}
                      {reviewResult.findings?.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-xs font-semibold uppercase text-slate-400">Review Findings</div>
                          {reviewResult.findings.map((f: any, idx: number) => (
                            <div
                              key={idx}
                              className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1.5 font-mono"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-indigo-300 font-semibold">
                                  {f.file}:{f.line}
                                </span>
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-950 text-amber-300 border border-amber-800">
                                  {f.category}
                                </span>
                              </div>
                              <p className="text-slate-300 font-sans">{f.message}</p>
                              {f.recommendation && (
                                <p className="text-slate-400 font-sans text-[11px]">
                                  <span className="font-semibold text-slate-300">Suggestion:</span> {f.recommendation}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Positive Observations */}
                      {reviewResult.positive_observations?.length > 0 && (
                        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/30 text-xs space-y-2">
                          <div className="font-bold text-emerald-400 flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Positive Observations</span>
                          </div>
                          <ul className="space-y-1 text-slate-300">
                            {reviewResult.positive_observations.map((obs: string, idx: number) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-emerald-400">•</span>
                                <span>{obs}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                      <Sparkles className="w-8 h-8 text-indigo-400 mx-auto" />
                      <p className="text-xs text-slate-400 max-w-sm mx-auto">
                        Click 'Run AI Review' to trigger Gemini 2.5 Flash analysis of this pull request's diff and code changes.
                      </p>
                      <button
                        onClick={handleRunAIReview}
                        disabled={isReviewing}
                        className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-500 transition"
                      >
                        Run AI Review Now
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-sm">
              Select a Pull Request to view its files, diff, and verification console.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
