export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'error';
  project: string;
  version: string;
  environment: string;
  database: {
    connected: boolean;
    url_driver: string;
  };
  sandbox: {
    mode: 'container' | 'disabled';
    max_memory_mb: number;
    timeout_seconds: number;
    cpu_quota: number;
  };
  timestamp: string;
}

