import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, CheckCircle2, X, Sparkles, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  onAnalyze: (files: File[]) => void;
  errorMessage?: string | null;
}

const SUPPORTED = [".rpt", ".txt", ".xdc", ".log"];

export const UploadHero = ({ onAnalyze, errorMessage }: Props) => {
  const [fileObjs, setFileObjs] = useState<File[]>([]);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((incoming: File[]) => {
    setFileObjs((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...incoming.filter((f) => !existing.has(f.name))];
    });
  }, []);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    addFiles(Array.from(e.dataTransfer.files));
  };

  const onInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(Array.from(e.target.files));
  };

  const handleAnalyze = () => {
    if (fileObjs.length === 0) return;
    onAnalyze(fileObjs);
  };

  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-mesh" />
      <div className="absolute inset-0 grid-bg opacity-30" />
      <div className="relative mx-auto max-w-5xl px-6 py-20 md:py-28">

        {/* Hero text */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-10 text-center">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-surface-elevated px-3 py-1 text-xs font-medium shadow-elev-sm">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inset-0 animate-ping rounded-full bg-ai opacity-75" />
              <span className="relative h-1.5 w-1.5 rounded-full bg-ai" />
            </span>
            AI engine online · XGBoost + MLP Ensemble
          </div>
          <h1 className="text-balance text-4xl font-semibold tracking-tight md:text-5xl lg:text-6xl">
            FPGA Intelligence,
            <br />
            <span className="text-gradient-ai">decoded in seconds.</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-balance text-base text-muted-foreground md:text-lg">
            Upload your Vivado reports. The AI engine — trained on 200,000 real FPGA designs — surfaces
            critical paths, power hotspots, and routing risks, then generates precise fixes.
          </p>
        </motion.div>

        {/* Error banner */}
        <AnimatePresence>
          {errorMessage && (
            <motion.div
              initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="mx-auto mb-6 flex max-w-2xl items-center gap-3 rounded-xl border border-error/40 bg-error/5 px-4 py-3 text-sm text-error"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Upload zone */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mx-auto max-w-3xl">
          <input ref={inputRef} type="file" multiple accept={SUPPORTED.join(",")} className="hidden" onChange={onInput} />

          <div
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
            className={`relative rounded-2xl border-2 border-dashed bg-surface-elevated p-8 shadow-elev-md transition-all md:p-10 ${
              drag ? "border-primary bg-primary/5 scale-[1.01]" : "border-border"
            }`}
          >
            <div className="text-center">
              <motion.div animate={drag ? { y: -4 } : { y: 0 }} className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-ai shadow-ai-glow">
                <UploadCloud className="h-7 w-7 text-white" />
              </motion.div>
              <p className="text-base font-medium">Drop Vivado reports here</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Supports <code className="rounded bg-muted px-1 text-xs">.rpt</code>{" "}
                <code className="rounded bg-muted px-1 text-xs">.txt</code>{" "}
                <code className="rounded bg-muted px-1 text-xs">.xdc</code> · up to 50 MB each
              </p>
              <p className="mt-2 text-xs text-muted-foreground opacity-75">
                Expected: <span className="font-mono">power.rpt · timing.rpt · utilization.rpt · drc.rpt</span>
              </p>

              <div className="mt-5 flex flex-wrap justify-center gap-2">
                <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
                  <FileText className="mr-1.5 h-3.5 w-3.5" /> Browse files
                </Button>
              </div>
            </div>

            <AnimatePresence>
              {fileObjs.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                  className="mt-6 overflow-hidden border-t border-border pt-5"
                >
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {fileObjs.length} file{fileObjs.length > 1 ? "s" : ""} staged for upload
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {fileObjs.map((f, i) => {
                      const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
                      const valid = SUPPORTED.includes(`.${ext}`);
                      return (
                        <motion.div
                          key={f.name}
                          initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}
                          className="flex items-center gap-2.5 rounded-lg border border-border bg-surface px-3 py-2 text-sm"
                        >
                          {valid
                            ? <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
                            : <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                          }
                          <span className="flex-1 truncate font-mono text-xs">{f.name}</span>
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {(f.size / 1024).toFixed(0)} KB
                          </span>
                          <button onClick={() => setFileObjs((p) => p.filter((x) => x.name !== f.name))} className="text-muted-foreground hover:text-foreground">
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </motion.div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="mt-6 flex flex-col items-center gap-2">
            <Button
              size="lg"
              onClick={handleAnalyze}
              disabled={fileObjs.length === 0}
              className="gap-2 bg-gradient-ai text-white shadow-ai-glow hover:opacity-90 disabled:opacity-40"
            >
              <Sparkles className="h-4 w-4" />
              Analyze with AI
            </Button>
            {fileObjs.length === 0 && (
              <p className="text-xs text-muted-foreground">Select your Vivado report files above to begin</p>
            )}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};
