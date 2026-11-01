import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

interface StatusBadgeProps {
  status: 'healthy' | 'degraded' | 'error' | 'pending';
  label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label }) => {
  const configs = {
    healthy: {
      bg: 'bg-emerald-950/50 text-emerald-400 border-emerald-800/50',
      icon: CheckCircle2,
      text: label || 'Operational',
    },
    degraded: {
      bg: 'bg-amber-950/50 text-amber-400 border-amber-800/50',
      icon: AlertTriangle,
      text: label || 'Degraded',
    },
    error: {
      bg: 'bg-rose-950/50 text-rose-400 border-rose-800/50',
      icon: XCircle,
      text: label || 'Error',
    },
    pending: {
      bg: 'bg-slate-800 text-slate-400 border-slate-700',
      icon: Clock,
      text: label || 'Connecting...',
    },
  };

  const config = configs[status] || configs.pending;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.text}
    </span>
  );
};

