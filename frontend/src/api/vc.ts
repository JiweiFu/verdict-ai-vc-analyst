// VC analysis API client. Mirrors the FastAPI backend at /api/v1/vc/*.

import { fetchGet, fetchPost, getBaseURL } from '@/api/http';

export interface StartupInfo {
  name: string;
  description: string;
  [k: string]: unknown;
}

export interface MarketAnalysis {
  market_size: string;
  growth_potential: string;
  competition: string;
  market_viability_score: number;
  analysis: string;
}

export interface ProductAnalysis {
  innovation: string;
  scalability: string;
  product_market_fit: string;
  potential_score: number;
  analysis: string;
}

export interface FounderAnalysis {
  competency_score: number;
  segmentation: number;
  analysis: string;
}

export type Recommendation = 'Invest' | 'Hold' | 'Pass';

export interface IntegratedAnalysis {
  overall_assessment: string;
  recommendation: Recommendation;
  confidence: number;
  key_strengths: string[];
  key_risks: string[];
  rationale: string;
}

export interface VCAnalyzeResponse {
  startup_info: StartupInfo | null;
  market_analysis: MarketAnalysis | null;
  product_analysis: ProductAnalysis | null;
  founder_analysis: FounderAnalysis | null;
  final: IntegratedAnalysis | null;
}

export interface VCAnalyzeRequestBody {
  raw_input: string;
  provider: string;
  model: string;
  api_key: string;
  agent_feedback?: Record<string, string>;
}

export type VCNodeName = 'scout' | 'market' | 'product' | 'founder' | 'chief';

export type VCStreamEvent =
  | { type: 'node_start'; node: VCNodeName }
  | { type: 'node_complete'; node: VCNodeName; data: any }
  | { type: 'done'; result: VCAnalyzeResponse }
  | { type: 'error'; detail: string };

export interface VCStreamHandlers {
  onNodeStart(node: VCNodeName): void;
  onNodeComplete(node: VCNodeName, data: any): void;
  onDone(result: VCAnalyzeResponse): void;
  onError(detail: string): void;
}

export async function analyzeStartup(
  body: VCAnalyzeRequestBody
): Promise<VCAnalyzeResponse> {
  return (await fetchPost('/api/v1/vc/analyze', body)) as VCAnalyzeResponse;
}

export async function analyzeStartupStream(
  body: VCAnalyzeRequestBody,
  handlers: VCStreamHandlers
): Promise<void> {
  const baseURL = await getBaseURL();
  const resp = await fetch(`${baseURL}/api/v1/vc/analyze/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!resp.ok || !resp.body) {
    handlers.onError(
      `Stream request failed: ${resp.status} ${resp.statusText}`
    );
    return;
  }

  const dispatch = (event: VCStreamEvent): void => {
    switch (event.type) {
      case 'node_start':
        handlers.onNodeStart(event.node);
        break;
      case 'node_complete':
        handlers.onNodeComplete(event.node, event.data);
        break;
      case 'done':
        handlers.onDone(event.result);
        break;
      case 'error':
        handlers.onError(event.detail);
        break;
    }
  };

  const handleLine = (line: string): void => {
    const trimmed = line.trim();
    if (!trimmed) return;
    dispatch(JSON.parse(trimmed) as VCStreamEvent);
  };

  try {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let newlineIndex = buffer.indexOf('\n');
      while (newlineIndex !== -1) {
        const line = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);
        handleLine(line);
        newlineIndex = buffer.indexOf('\n');
      }
    }

    // Flush any remaining buffered complete line.
    handleLine(buffer);
  } catch (err) {
    handlers.onError(String(err));
  }
}

export async function vcHealthCheck(): Promise<boolean> {
  try {
    const r = await fetchGet('/api/v1/vc/health');
    return r?.status === 'ok';
  } catch {
    return false;
  }
}
