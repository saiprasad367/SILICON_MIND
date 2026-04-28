import { useState, useCallback, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { TopNav } from "@/components/dashboard/TopNav";
import { UploadHero } from "@/components/dashboard/UploadHero";
import { AnalysisLoader } from "@/components/dashboard/AnalysisLoader";
import { StatusBar } from "@/components/dashboard/StatusBar";
import { PowerSection } from "@/components/dashboard/PowerSection";
import { TimingSection } from "@/components/dashboard/TimingSection";
import { UtilizationSection } from "@/components/dashboard/UtilizationSection";
import { DrcSection } from "@/components/dashboard/DrcSection";
import { AiInsightsPanel } from "@/components/dashboard/AiInsightsPanel";
import { RecommendationsSection } from "@/components/dashboard/RecommendationsSection";
import { AnalyticsSection } from "@/components/dashboard/AnalyticsSection";
import { WhatIfSimulator } from "@/components/dashboard/WhatIfSimulator";
import { AutopilotSection } from "@/components/dashboard/AutopilotSection";
import { ClockSection } from "@/components/dashboard/ClockSection";
import { uploadFiles, fetchAnalysis, type AnalysisResponse } from "@/lib/api";
import { toast } from "sonner";

type Phase = "upload" | "loading" | "results";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:5000";

// Poll /api/analysis_ready until backend signals done
async function waitForAnalysis(timeoutMs = 60_000): Promise<AnalysisResponse> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE_URL}/api/analysis_ready`);
      const json = await res.json();
      if (json.error) throw new Error(json.error);
      if (json.ready) {
        return await fetchAnalysis();
      }
    } catch (e: any) {
      if (e.message && e.message !== "Failed to fetch") throw e;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error("Analysis timed out — backend took too long.");
}

const Index = () => {
  const [phase, setPhase] = useState<Phase>("upload");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const uploadedFiles = useRef<File[]>([]);

  const handleAnalyze = useCallback(async (files: File[]) => {
    if (!files || files.length === 0) {
      toast.error("Please select your Vivado report files before analyzing.");
      return;
    }
    uploadedFiles.current = files;
    setPhase("loading");
    setErrorMsg(null);

    try {
      // 1. Upload to backend
      await uploadFiles(files);
      // 2. Poll until analysis is ready
      const data = await waitForAnalysis(90_000);
      setAnalysis(data);
      setPhase("results");
      toast.success(`Analysis complete — ${data.design?.designStatus ?? "Done"}`);
    } catch (err: any) {
      const msg = err?.message ?? "Analysis failed.";
      setErrorMsg(msg);
      toast.error(msg);
      setPhase("upload");
    }
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <TopNav onUpload={() => { setPhase("upload"); setErrorMsg(null); }} onReset={() => { setPhase("upload"); setAnalysis(null); setErrorMsg(null); }} />

      <AnimatePresence mode="wait">
        {phase === "upload" && (
          <motion.main key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <UploadHero onAnalyze={handleAnalyze} errorMessage={errorMsg} />
          </motion.main>
        )}

        {phase === "loading" && (
          <motion.main key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <AnalysisLoader onDone={() => {}} />
          </motion.main>
        )}

        {phase === "results" && analysis && (
          <motion.main key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <StatusBar data={analysis as any} />
            <div className="mx-auto max-w-[1600px] space-y-5 px-6 py-6">
              <AutopilotSection analysisData={analysis} />

              <div className="grid gap-5 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <TimingSection data={analysis.timing as any} />
                </div>
                <AiInsightsPanel data={analysis.insights as any} />
              </div>

              <div className="grid gap-5 lg:grid-cols-2">
                <PowerSection data={analysis.power as any} />
                <UtilizationSection data={analysis.utilization as any} congestion={analysis.congestion as any} />
              </div>

              <div className="grid gap-5 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <AnalyticsSection data={analysis.powerVsPerf as any} />
                </div>
                <RecommendationsSection data={analysis.recommendations as any} />
              </div>

              <div className="grid gap-5 lg:grid-cols-2">
                <WhatIfSimulator baseFeatures={analysis} />
                <ClockSection clocks={analysis.clocks as any} cdc={analysis.cdcViolations} />
              </div>

              <DrcSection data={analysis.drc as any} />

              <footer className="py-8 text-center text-xs text-muted-foreground">
                SiliconMind FPGA Intelligence · Model: <b>{analysis.design?.modelUsed}</b>
                {" "}· Confidence: <b>{((analysis.design?.confidence ?? 0) * 100).toFixed(0)}%</b>
                {" "}· Strategy: <b>{analysis.bestStrategy}</b>
              </footer>
            </div>
          </motion.main>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Index;
