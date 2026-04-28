import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, ChevronDown, Download, Wrench } from "lucide-react";
import { SectionCard } from "./SectionCard";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";


const sevStyles = {
  error: { bg: "bg-error/10", text: "text-error", border: "border-error/30", label: "Error" },
  warning: { bg: "bg-warning/10", text: "text-warning", border: "border-warning/30", label: "Warning" },
  info: { bg: "bg-info/10", text: "text-info", border: "border-info/30", label: "Info" },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const DrcSection = ({ data }: { data: any[] }) => {
  const [open, setOpen] = useState<string | null>(data[0]?.id ?? null);

  const downloadXdc = () => {
    const xdc = data.map(d => `# Auto-fix for ${d.id} (${d.rule})\n# ${d.message}\n# Suggestion: ${d.fix}\n`).join("\n");
    const blob = new Blob([xdc], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "auto_constraints.xdc"; a.click();
    URL.revokeObjectURL(url);
    toast.success("auto_constraints.xdc downloaded");
  };

  return (
    <SectionCard
      title="DRC & Auto-Fix"
      subtitle={`${data.length} violations · auto-generated XDC available`}
      icon={<ShieldAlert className="h-4 w-4 text-error" />}
      action={
        <Button size="sm" variant="outline" onClick={downloadXdc} className="gap-1.5">
          <Download className="h-3.5 w-3.5" /> XDC
        </Button>
      }
      delay={0.2}
    >
      <div className="space-y-2">
        {data.map((d, i) => {
          const s = sevStyles[d.severity];
          const expanded = open === d.id;
          return (
            <motion.div
              key={d.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.04 * i }}
              className={`overflow-hidden rounded-lg border ${s.border}`}
            >
              <button
                onClick={() => setOpen(expanded ? null : d.id)}
                className={`flex w-full items-center gap-3 p-3 text-left ${s.bg}`}
              >
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${s.text} bg-background`}>{s.label}</span>
                <span className="font-mono text-[11px] text-muted-foreground">{d.rule}</span>
                <span className="flex-1 truncate text-sm">{d.message}</span>
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`} />
              </button>
              <AnimatePresence>
                {expanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden bg-card"
                  >
                    <div className="flex items-start gap-3 border-t border-border p-3">
                      <Wrench className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ai" />
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">AI fix</p>
                        <p className="mt-0.5 font-mono text-xs">{d.fix}</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </SectionCard>
  );
};
