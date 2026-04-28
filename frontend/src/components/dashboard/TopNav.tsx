import { motion } from "framer-motion";
import { Cpu, Search, Upload, Download, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  onUpload: () => void;
  onReset: () => void;
}

export const TopNav = ({ onUpload, onReset }: Props) => (
  <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
    <div className="flex h-14 items-center justify-between px-6">
      <div className="flex items-center gap-2.5">
        <motion.div
          initial={{ rotate: -90, opacity: 0 }}
          animate={{ rotate: 0, opacity: 1 }}
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-ai shadow-ai-glow"
        >
          <Cpu className="h-4 w-4 text-white" />
        </motion.div>
        <div className="flex items-baseline gap-2">
          <span className="font-semibold tracking-tight">SiliconMind</span>
          <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
            FPGA Intelligence
          </span>
        </div>
      </div>

      <div className="hidden flex-1 max-w-md mx-8 md:block">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            placeholder="Search modules, paths, signals…"
            className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-12 text-sm outline-none transition-colors focus:border-primary focus:bg-background"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            /
          </kbd>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onReset} className="gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" /> <span className="hidden sm:inline">Reset</span>
        </Button>
        <Button variant="ghost" size="sm" className="gap-1.5">
          <Download className="h-3.5 w-3.5" /> <span className="hidden sm:inline">Report</span>
        </Button>
        <Button size="sm" onClick={onUpload} className="gap-1.5 bg-gradient-ai text-white hover:opacity-90">
          <Sparkles className="h-3.5 w-3.5" /> New Analysis
        </Button>
      </div>
    </div>
  </header>
);
