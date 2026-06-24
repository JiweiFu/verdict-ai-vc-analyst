// Startup Evaluation page: collects a startup description, streams the multi-agent
// VC analysis, and renders specialist + synthesis results incrementally.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Circle,
  Loader2,
  MessageSquarePlus,
  RefreshCw,
  Settings as SettingsIcon,
  Sparkles,
} from 'lucide-react';

import {
  analyzeStartupStream,
  type FounderAnalysis,
  type IntegratedAnalysis,
  type MarketAnalysis,
  type ProductAnalysis,
  type Recommendation,
  type VCNodeName,
} from '@/api/vc';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  defaultModelFor,
  useVCSettingsStore,
  VC_PROVIDERS,
  type VCProvider,
} from '@/store/vcSettingsStore';

type BadgeTone = 'success' | 'warning' | 'error' | 'neutral';

function recommendationTone(rec: Recommendation): BadgeTone {
  if (rec === 'Invest') return 'success';
  if (rec === 'Hold') return 'warning';
  return 'error';
}

function ScoreBadge({ label }: { label: string }) {
  return (
    <Badge variant="secondary" tone="information">
      {label}
    </Badge>
  );
}

function LabeledLine({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-label-xs uppercase tracking-wide text-ds-text-neutral-muted-default">
        {label}
      </span>
      <span className="text-body-sm text-ds-text-neutral-default-default">
        {value}
      </span>
    </div>
  );
}

function SpecialistCard({
  title,
  scoreLabel,
  extraBadge,
  details,
  analysis,
}: {
  title: string;
  scoreLabel: string;
  extraBadge?: React.ReactNode;
  details?: React.ReactNode;
  analysis: string;
}) {
  return (
    <Card className="border-ds-border-neutral-default-default bg-ds-bg-neutral-default-default">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-body-lg">{title}</CardTitle>
          <div className="flex items-center gap-1.5">
            <ScoreBadge label={scoreLabel} />
            {extraBadge}
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {details ? <div className="flex flex-col gap-2">{details}</div> : null}
        <p className="text-body-sm leading-relaxed text-ds-text-neutral-default-default">
          {analysis}
        </p>
      </CardContent>
    </Card>
  );
}

function RecommendationBanner({ final }: { final: IntegratedAnalysis }) {
  const tone = recommendationTone(final.recommendation);
  return (
    <Card className="border-ds-border-neutral-default-default bg-ds-bg-neutral-default-default">
      <CardContent className="flex flex-col gap-3 p-6">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="primary" tone={tone} size="sm">
            {final.recommendation}
          </Badge>
          <span className="text-body-sm text-ds-text-neutral-muted-default">
            Confidence: {Math.round(final.confidence * 100)}%
          </span>
        </div>
        <p className="text-body-md leading-relaxed text-ds-text-neutral-default-default">
          {final.overall_assessment}
        </p>
      </CardContent>
    </Card>
  );
}

function MarketCard({ data }: { data: MarketAnalysis }) {
  return (
    <SpecialistCard
      title="Market"
      scoreLabel={`${data.market_viability_score}/10`}
      analysis={data.analysis}
      details={
        <>
          <LabeledLine label="Market size" value={data.market_size} />
          <LabeledLine label="Growth" value={data.growth_potential} />
          <LabeledLine label="Competition" value={data.competition} />
        </>
      }
    />
  );
}

function ProductCard({ data }: { data: ProductAnalysis }) {
  return (
    <SpecialistCard
      title="Product"
      scoreLabel={`${data.potential_score}/10`}
      analysis={data.analysis}
      details={
        <>
          <LabeledLine label="Innovation" value={data.innovation} />
          <LabeledLine label="Scalability" value={data.scalability} />
          <LabeledLine
            label="Product-market fit"
            value={data.product_market_fit}
          />
        </>
      }
    />
  );
}

function FounderCard({ data }: { data: FounderAnalysis }) {
  return (
    <SpecialistCard
      title="Founder"
      scoreLabel={`${data.competency_score}/10`}
      extraBadge={
        <Badge variant="secondary" tone="neutral">
          L{data.segmentation}
        </Badge>
      }
      analysis={data.analysis}
    />
  );
}

function SynthesisCard({ final }: { final: IntegratedAnalysis }) {
  return (
    <Card className="border-ds-border-neutral-default-default bg-ds-bg-neutral-default-default">
      <CardHeader className="pb-3">
        <CardTitle className="text-body-lg">Chief Investor Synthesis</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-body-sm leading-relaxed text-ds-text-neutral-default-default">
          {final.rationale}
        </p>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <div className="flex flex-col gap-2">
            <h4 className="flex items-center gap-1.5 text-label-sm font-semibold text-ds-text-status-completed-strong-default">
              <CheckCircle2 className="h-4 w-4" />
              Key strengths
            </h4>
            <ul className="flex flex-col gap-1.5">
              {final.key_strengths.map((s, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-body-sm text-ds-text-neutral-default-default"
                >
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ds-text-status-completed-strong-default" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col gap-2">
            <h4 className="flex items-center gap-1.5 text-label-sm font-semibold text-ds-text-status-error-strong-default">
              <AlertTriangle className="h-4 w-4" />
              Key risks
            </h4>
            <ul className="flex flex-col gap-1.5">
              {final.key_risks.map((r, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-body-sm text-ds-text-neutral-default-default"
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ds-text-status-error-strong-default" />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---- Streaming progress + refine plumbing ----

type NodeState = 'pending' | 'running' | 'done';
type ProgressMap = Record<VCNodeName, NodeState>;
// Refine feedback is keyed by the analyst node names only.
type FeedbackKey = 'market' | 'product' | 'founder' | 'chief';

const PIPELINE: { node: VCNodeName; label: string }[] = [
  { node: 'scout', label: 'Parsing' },
  { node: 'market', label: 'Market' },
  { node: 'product', label: 'Product' },
  { node: 'founder', label: 'Founder' },
  { node: 'chief', label: 'Chief synthesis' },
];

const ALL_NODES: VCNodeName[] = PIPELINE.map((p) => p.node);

function initialProgress(): ProgressMap {
  return {
    scout: 'pending',
    market: 'pending',
    product: 'pending',
    founder: 'pending',
    chief: 'pending',
  };
}

function ProgressRow({ label, state }: { label: string; state: NodeState }) {
  return (
    <div className="flex items-center gap-2.5">
      {state === 'done' ? (
        <Check className="h-4 w-4 shrink-0 text-ds-text-status-completed-strong-default" />
      ) : state === 'running' ? (
        <Loader2 className="h-4 w-4 shrink-0 animate-spin text-ds-text-information-default-default" />
      ) : (
        <Circle className="h-4 w-4 shrink-0 text-ds-text-neutral-muted-default" />
      )}
      <span
        className={
          state === 'pending'
            ? 'text-body-sm text-ds-text-neutral-muted-default'
            : 'text-body-sm text-ds-text-neutral-default-default'
        }
      >
        {label}
      </span>
    </div>
  );
}

// Collapsible refine box composed around an existing card; never edits the card.
function RefineWrap({
  node,
  value,
  onChange,
  children,
}: {
  node: FeedbackKey;
  value: string;
  onChange: (node: FeedbackKey, text: string) => void;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex flex-col gap-2">
      {children}
      <div className="flex flex-col gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => setOpen((o) => !o)}
        >
          <MessageSquarePlus className="h-4 w-4" />
          {open ? 'Hide refine' : 'Refine'}
          {!open && value.trim() ? (
            <Badge variant="secondary" tone="information" size="sm">
              edited
            </Badge>
          ) : null}
        </Button>
        {open ? (
          <Textarea
            rows={3}
            value={value}
            onChange={(e) => onChange(node, e.target.value)}
            placeholder="Add context or a correction for this agent…"
            className="text-body-sm"
          />
        ) : null}
      </div>
    </div>
  );
}

export default function VCAnalysis() {
  const navigate = useNavigate();

  const initialProvider = useVCSettingsStore((s) => s.provider);
  const apiKeys = useVCSettingsStore((s) => s.apiKeys);

  const [rawInput, setRawInput] = useState('');
  const [provider, setProvider] = useState<VCProvider>(initialProvider);
  const [model, setModel] = useState<string>(defaultModelFor(initialProvider));

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasCompleted, setHasCompleted] = useState(false);

  // Streaming progress + incremental result state.
  const [progress, setProgress] = useState<ProgressMap>(initialProgress);
  const [market, setMarket] = useState<MarketAnalysis | null>(null);
  const [product, setProduct] = useState<ProductAnalysis | null>(null);
  const [founder, setFounder] = useState<FounderAnalysis | null>(null);
  const [final, setFinal] = useState<IntegratedAnalysis | null>(null);

  // Refine feedback keyed by analyst node.
  const [agentFeedback, setAgentFeedback] = useState<Record<string, string>>(
    {}
  );

  const apiKey = apiKeys[provider] ?? '';
  const hasKey = apiKey.trim().length > 0;
  const canAnalyze = rawInput.trim().length > 0 && hasKey && !loading;
  const canRerun = hasCompleted && !loading && hasKey;

  const handleProviderChange = (value: string) => {
    const next = value as VCProvider;
    setProvider(next);
    setModel(defaultModelFor(next));
  };

  const handleFeedbackChange = (node: FeedbackKey, text: string) => {
    setAgentFeedback((prev) => ({ ...prev, [node]: text }));
  };

  const setNodeState = (node: VCNodeName, state: NodeState) => {
    setProgress((prev) => ({ ...prev, [node]: state }));
  };

  // Runs a fresh stream. `feedback` is sent as agent_feedback; first run omits it.
  const runStream = async (feedback?: Record<string, string>) => {
    setLoading(true);
    setError(null);
    setHasCompleted(false);
    setProgress(initialProgress());
    setMarket(null);
    setProduct(null);
    setFounder(null);
    setFinal(null);

    await analyzeStartupStream(
      {
        raw_input: rawInput,
        provider,
        model,
        api_key: apiKey,
        ...(feedback && Object.keys(feedback).length > 0
          ? { agent_feedback: feedback }
          : {}),
      },
      {
        onNodeStart: (node) => setNodeState(node, 'running'),
        onNodeComplete: (node, data) => {
          setNodeState(node, 'done');
          if (node === 'market') setMarket(data as MarketAnalysis);
          else if (node === 'product') setProduct(data as ProductAnalysis);
          else if (node === 'founder') setFounder(data as FounderAnalysis);
          else if (node === 'chief') setFinal(data as IntegratedAnalysis);
        },
        onDone: (res) => {
          // Reconcile any nodes still mid-flight and backfill cards.
          setProgress((prev) => {
            const next = { ...prev };
            for (const n of ALL_NODES) next[n] = 'done';
            return next;
          });
          if (res.market_analysis) setMarket(res.market_analysis);
          if (res.product_analysis) setProduct(res.product_analysis);
          if (res.founder_analysis) setFounder(res.founder_analysis);
          if (res.final) setFinal(res.final);
          setLoading(false);
          setHasCompleted(true);
        },
        onError: (detail) => {
          setError(detail);
          // Stop spinners: anything still running drops back to pending.
          setProgress((prev) => {
            const next = { ...prev };
            for (const n of ALL_NODES) {
              if (next[n] === 'running') next[n] = 'pending';
            }
            return next;
          });
          setLoading(false);
          setHasCompleted(true);
        },
      }
    );
  };

  const handleAnalyze = () => {
    void runStream();
  };

  const handleRerun = () => {
    void runStream(agentFeedback);
  };

  const hasResults = Boolean(market || product || founder || final);
  const showProgress = loading || hasResults;

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-10">
        {/* Header */}
        <div className="flex flex-col gap-1">
          <h1 className="text-heading-h3 font-semibold text-ds-text-neutral-default-default">
            Startup Evaluation
          </h1>
          <p className="text-body-sm text-ds-text-neutral-muted-default">
            Paste a startup description and get a multi-agent VC assessment of
            market, product, founder, and an overall recommendation.
          </p>
        </div>

        {/* Input card */}
        <Card className="border-ds-border-neutral-default-default bg-ds-bg-neutral-default-default">
          <CardHeader className="pb-3">
            <CardTitle className="text-body-lg">Startup details</CardTitle>
            <CardDescription>
              Describe the company, market, product, and team.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="vc-raw-input">Description</Label>
              <Textarea
                id="vc-raw-input"
                rows={8}
                value={rawInput}
                onChange={(e) => setRawInput(e.target.value)}
                placeholder="e.g. Acme is a seed-stage B2B SaaS building AI-powered contract review for mid-market legal teams. Founded by two ex-Stripe engineers. $40k MRR, growing 15% MoM..."
                className="min-h-[180px]"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label>Provider</Label>
                <Select value={provider} onValueChange={handleProviderChange}>
                  <SelectTrigger wrapperClassName="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VC_PROVIDERS.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="vc-model">Model</Label>
                <Input
                  id="vc-model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="Model id"
                />
              </div>
            </div>

            {!hasKey ? (
              <Alert tone="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>No API key set for {provider}.</AlertTitle>
                <AlertDescription className="flex flex-col gap-2">
                  <span>Add one in Settings to run an analysis.</span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-fit"
                    onClick={() => navigate('/settings')}
                  >
                    <SettingsIcon className="h-4 w-4" />
                    Open Settings
                  </Button>
                </AlertDescription>
              </Alert>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="primary"
                size="lg"
                className="w-fit"
                disabled={!canAnalyze}
                onClick={handleAnalyze}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                {loading ? 'Analyzing…' : 'Analyze'}
              </Button>

              {hasCompleted || hasResults ? (
                <Button
                  variant="outline"
                  size="lg"
                  className="w-fit"
                  disabled={!canRerun}
                  onClick={handleRerun}
                >
                  <RefreshCw className="h-4 w-4" />
                  Rerun analysis
                </Button>
              ) : null}
            </div>

            {error ? (
              <Alert tone="error">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Analysis failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>

        {/* Pipeline progress */}
        {showProgress ? (
          <Card className="border-ds-border-neutral-default-default bg-ds-bg-neutral-default-default">
            <CardHeader className="pb-3">
              <CardTitle className="text-body-lg">Pipeline</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2.5">
              {PIPELINE.map((p) => (
                <ProgressRow
                  key={p.node}
                  label={p.label}
                  state={progress[p.node]}
                />
              ))}
            </CardContent>
          </Card>
        ) : null}

        {/* Results — rendered incrementally as nodes complete */}
        {hasResults ? (
          <div className="flex flex-col gap-6">
            {final ? <RecommendationBanner final={final} /> : null}

            {market || product || founder ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {market ? (
                  <RefineWrap
                    node="market"
                    value={agentFeedback.market ?? ''}
                    onChange={handleFeedbackChange}
                  >
                    <MarketCard data={market} />
                  </RefineWrap>
                ) : null}
                {product ? (
                  <RefineWrap
                    node="product"
                    value={agentFeedback.product ?? ''}
                    onChange={handleFeedbackChange}
                  >
                    <ProductCard data={product} />
                  </RefineWrap>
                ) : null}
                {founder ? (
                  <RefineWrap
                    node="founder"
                    value={agentFeedback.founder ?? ''}
                    onChange={handleFeedbackChange}
                  >
                    <FounderCard data={founder} />
                  </RefineWrap>
                ) : null}
              </div>
            ) : null}

            {final ? (
              <RefineWrap
                node="chief"
                value={agentFeedback.chief ?? ''}
                onChange={handleFeedbackChange}
              >
                <SynthesisCard final={final} />
              </RefineWrap>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
