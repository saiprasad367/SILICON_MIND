import { motion } from "framer-motion";
import { ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  badge?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  delay?: number;
}

export const SectionCard = ({ title, subtitle, icon, badge, action, children, className = "", delay = 0 }: Props) => (
  <motion.section
    initial={{ opacity: 0, y: 16 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-50px" }}
    transition={{ duration: 0.45, delay, ease: "easeOut" }}
    className={`group rounded-2xl border border-border bg-card shadow-elev-sm transition-shadow hover:shadow-elev-md ${className}`}
  >
    <div className="flex items-start justify-between gap-4 border-b border-border p-5">
      <div className="flex items-start gap-3">
        {icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface text-foreground">
            {icon}
          </div>
        )}
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold tracking-tight">{title}</h3>
            {badge}
          </div>
          {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
    <div className="p-5">{children}</div>
  </motion.section>
);
