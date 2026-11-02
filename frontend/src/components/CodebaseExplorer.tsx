import React, { useState, useEffect } from 'react';
import {
  Folder,
  FileCode,
  FileText,
  File,
  ChevronRight,
  ChevronDown,
  GitBranch,
  Copy,
  Check,
  RotateCw,
  Code2,
} from 'lucide-react';
import { fetchRepositoryTree, fetchRepositoryBlob, fetchRepositoryBranches } from '../services/api';

interface CodebaseExplorerProps {
  repositoryId: string;
}

interface TreeItem {
  path: string;
  type: string;
  size?: number;
  sha: string;
}

export const CodebaseExplorer: React.FC<CodebaseExplorerProps> = ({ repositoryId }) => {
  const [tree, setTree] = useState<TreeItem[]>([]);
  const [branches, setBranches] = useState<Array<{ name: string; commit_sha: string }>>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [selectedPath, setSelectedPath] = useState<string>('sample_app/calculator.py');
  const [fileContent, setFileContent] = useState<string>('');
  const [fileMeta, setFileMeta] = useState<{ lines: number; size: number; language: string } | null>(null);
  const [loadingTree, setLoadingTree] = useState<boolean>(true);
  const [loadingFile, setLoadingFile] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    sample_app: true,
    tests: true,
  });

  // Load branches & tree
  useEffect(() => {
    if (!repositoryId) return;
    const loadInit = async () => {
      setLoadingTree(true);
      try {
        const [branchList, treeData] = await Promise.all([
          fetchRepositoryBranches(repositoryId).catch(() => [{ name: 'main', commit_sha: '' }]),
          fetchRepositoryTree(repositoryId, selectedBranch),
        ]);
        setBranches(branchList);
        setTree(treeData.tree || []);
        
        // Pick first blob if default not found
        const hasDefault = treeData.tree?.some((t) => t.path === selectedPath);
        if (!hasDefault && treeData.tree?.length) {
          const firstBlob = treeData.tree.find((t) => t.type === 'blob');
          if (firstBlob) setSelectedPath(firstBlob.path);
        }
      } catch (err) {
        console.error('Failed to load codebase explorer:', err);
      } finally {
        setLoadingTree(false);
      }
    };
    loadInit();
  }, [repositoryId, selectedBranch]);

  // Load active file content
  useEffect(() => {
    if (!repositoryId || !selectedPath) return;
    const loadContent = async () => {
      setLoadingFile(true);
      try {
        const data = await fetchRepositoryBlob(repositoryId, selectedPath, selectedBranch);
        setFileContent(data.content);
        setFileMeta({ lines: data.lines, size: data.size, language: data.language });
      } catch (err) {
        setFileContent('// Failed to load file content from GitHub repository.');
      } finally {
        setLoadingFile(false);
      }
    };
    loadContent();
  }, [repositoryId, selectedPath, selectedBranch]);

  const handleCopy = () => {
    navigator.clipboard.writeText(fileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleFolder = (folderName: string) => {
    setExpandedFolders((prev) => ({ ...prev, [folderName]: !prev[folderName] }));
  };

  // Group tree items by folder
  const folders: Record<string, TreeItem[]> = { '/': [] };
  tree.forEach((item) => {
    if (item.type === 'tree') {
      if (!folders[item.path]) folders[item.path] = [];
    } else {
      const parts = item.path.split('/');
      if (parts.length === 1) {
        folders['/'].push(item);
      } else {
        const folder = parts.slice(0, -1).join('/');
        if (!folders[folder]) folders[folder] = [];
        folders[folder].push(item);
      }
    }
  });

  const getFileIcon = (path: string) => {
    if (path.endsWith('.py')) return <FileCode className="w-4 h-4 text-emerald-400 shrink-0" />;
    if (path.endsWith('.md')) return <FileText className="w-4 h-4 text-sky-400 shrink-0" />;
    if (path.endsWith('.json') || path.endsWith('.yml')) return <Code2 className="w-4 h-4 text-amber-400 shrink-0" />;
    return <File className="w-4 h-4 text-slate-400 shrink-0" />;
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Code2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Codebase Explorer</h2>
            <p className="text-xs text-slate-400">
              Interactive GitHub repository filesystem with live Git Blob retrieval and syntax inspection.
            </p>
          </div>
        </div>

        {/* Branch Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300">
            <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              {branches.map((b) => (
                <option key={b.name} value={b.name} className="bg-slate-900 text-slate-200">
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          <span className="text-xs text-slate-500 font-mono">
            {tree.filter((t) => t.type === 'blob').length} files indexed
          </span>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: File Tree */}
        <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col h-[700px]">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 px-2 flex items-center justify-between">
            <span>Repository Tree</span>
            {loadingTree && <RotateCw className="w-3 h-3 text-indigo-400 animate-spin" />}
          </div>

          <div className="flex-1 overflow-y-auto space-y-1 font-mono text-xs pr-1">
            {/* Root-level files */}
            {folders['/']?.map((item) => (
              <button
                key={item.path}
                onClick={() => setSelectedPath(item.path)}
                className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left transition ${
                  selectedPath === item.path
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                {getFileIcon(item.path)}
                <span className="truncate">{item.path}</span>
              </button>
            ))}

            {/* Subfolders */}
            {Object.keys(folders)
              .filter((k) => k !== '/')
              .map((folder) => {
                const isExpanded = expandedFolders[folder] ?? true;
                return (
                  <div key={folder} className="space-y-0.5">
                    <button
                      onClick={() => toggleFolder(folder)}
                      className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-left text-slate-300 hover:bg-slate-800 transition font-medium"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                      )}
                      <Folder className="w-4 h-4 text-indigo-400 fill-indigo-400/20 shrink-0" />
                      <span className="truncate">{folder}</span>
                    </button>

                    {isExpanded && (
                      <div className="ml-4 pl-2 border-l border-slate-800 space-y-0.5">
                        {folders[folder]?.map((item) => (
                          <button
                            key={item.path}
                            onClick={() => setSelectedPath(item.path)}
                            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition ${
                              selectedPath === item.path
                                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 font-medium'
                                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                            }`}
                          >
                            {getFileIcon(item.path)}
                            <span className="truncate">{item.path.split('/').pop()}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>

        {/* Right Column: Code Viewer */}
        <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[700px]">
          {/* File Tab Bar */}
          <div className="bg-slate-950/80 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getFileIcon(selectedPath)}
              <span className="font-mono text-xs font-semibold text-white">{selectedPath}</span>
              {fileMeta && (
                <span className="text-[11px] text-slate-500 font-mono ml-2">
                  {fileMeta.lines} lines • {Math.round(fileMeta.size)} B • {fileMeta.language}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Source Code Content with Line Numbers */}
          <div className="flex-1 overflow-auto bg-slate-950 p-4 font-mono text-xs leading-relaxed select-text">
            {loadingFile ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs gap-2">
                <RotateCw className="w-4 h-4 animate-spin text-indigo-400" />
                <span>Fetching raw blob from GitHub...</span>
              </div>
            ) : (
              <table className="w-full border-collapse">
                <tbody>
                  {fileContent.split('\n').map((line, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/60 transition-colors">
                      <td className="w-10 pr-4 text-right text-slate-600 select-none font-mono text-[11px] align-top">
                        {idx + 1}
                      </td>
                      <td className="text-slate-200 whitespace-pre font-mono">{line || ' '}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
