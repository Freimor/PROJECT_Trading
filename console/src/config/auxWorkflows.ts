/** Auxiliary n8n workflows — not toggled from Crypto/MOEX desks. */
export type AuxWorkflowMeta = {
  scheduleKey: string;
  purposeKey: string;
};

export const AUX_WORKFLOW_META: Record<string, AuxWorkflowMeta> = {
  "news-ingest": {
    scheduleKey: "workflowsPage.aux.newsIngest.schedule",
    purposeKey: "workflowsPage.aux.newsIngest.purpose",
  },
  "regulatory-monitor": {
    scheduleKey: "workflowsPage.aux.regulatoryMonitor.schedule",
    purposeKey: "workflowsPage.aux.regulatoryMonitor.purpose",
  },
  "analysis-llm-report": {
    scheduleKey: "workflowsPage.aux.analysisLlmReport.schedule",
    purposeKey: "workflowsPage.aux.analysisLlmReport.purpose",
  },
  "llm-benchmark-weekly": {
    scheduleKey: "workflowsPage.aux.llmBenchmark.schedule",
    purposeKey: "workflowsPage.aux.llmBenchmark.purpose",
  },
  "papers-monitor-weekly": {
    scheduleKey: "workflowsPage.aux.papersMonitor.schedule",
    purposeKey: "workflowsPage.aux.papersMonitor.purpose",
  },
  "neuratrade-harness": {
    scheduleKey: "workflowsPage.aux.neuratradeHarness.schedule",
    purposeKey: "workflowsPage.aux.neuratradeHarness.purpose",
  },
  "finsaber-backtest-weekly": {
    scheduleKey: "workflowsPage.aux.finsaberBacktest.schedule",
    purposeKey: "workflowsPage.aux.finsaberBacktest.purpose",
  },
  "deepfund-live-paper": {
    scheduleKey: "workflowsPage.aux.deepfundLivePaper.schedule",
    purposeKey: "workflowsPage.aux.deepfundLivePaper.purpose",
  },
  "shared-global-error-handler": {
    scheduleKey: "workflowsPage.aux.sharedError.schedule",
    purposeKey: "workflowsPage.aux.sharedError.purpose",
  },
  "shared-health-check": {
    scheduleKey: "workflowsPage.aux.sharedHealth.schedule",
    purposeKey: "workflowsPage.aux.sharedHealth.purpose",
  },
  "shared-telegram-alert": {
    scheduleKey: "workflowsPage.aux.sharedTelegram.schedule",
    purposeKey: "workflowsPage.aux.sharedTelegram.purpose",
  },
  "securities-factor-sleeve": {
    scheduleKey: "workflowsPage.aux.factorSleeve.schedule",
    purposeKey: "workflowsPage.aux.factorSleeve.purpose",
  },
  "bond-ladder-flow": {
    scheduleKey: "workflowsPage.aux.bondLadder.schedule",
    purposeKey: "workflowsPage.aux.bondLadder.purpose",
  },
  "crypto-scalp-hybrid-dry-run": {
    scheduleKey: "workflowsPage.aux.cryptoScalpDry.schedule",
    purposeKey: "workflowsPage.aux.cryptoScalpDry.purpose",
  },
  "crypto-scalp-hybrid-paper": {
    scheduleKey: "workflowsPage.aux.cryptoScalpPaper.schedule",
    purposeKey: "workflowsPage.aux.cryptoScalpPaper.purpose",
  },
  "crypto-execute-testnet": {
    scheduleKey: "workflowsPage.aux.cryptoExecute.schedule",
    purposeKey: "workflowsPage.aux.cryptoExecute.purpose",
  },
};
