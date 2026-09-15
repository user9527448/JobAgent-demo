import {
  BriefcaseBusiness,
  FileText,
  History,
  House,
  Menu,
  Send,
  Settings,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import type { HealthSnapshot } from "../lib/api";
import { cn } from "../lib/utils";
import { Badge } from "./ui/badge";
import { Sheet, SheetClose, SheetContent, SheetTrigger } from "./ui/sheet";

const navigation = [
  { label: "今日简报", icon: House, current: true },
  { label: "职位机会", icon: BriefcaseBusiness, current: false },
  { label: "运行记录", icon: History, current: false },
  { label: "投递管理", icon: Send, current: false },
  { label: "设置", icon: Settings, current: false },
] as const;

interface AppShellProps {
  children: ReactNode;
  health: HealthSnapshot;
  timezone?: string;
}

export function AppShell({
  children,
  health,
  timezone = "Asia/Shanghai",
}: AppShellProps) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 flex h-[68px] items-center border-b border-border bg-background/95 px-4 backdrop-blur md:px-6">
        <div className="mx-auto flex w-full max-w-[1484px] items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <MobileNavigation />
            <a
              className="rounded-sm text-lg font-extrabold tracking-[-0.02em] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:text-[22px]"
              href="/app/"
            >
              JOBAGENT{" "}
              <span className="font-semibold text-muted-foreground">
                招聘情报
              </span>
            </a>
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground sm:gap-5">
            <SystemHealth health={health} />
            <span
              aria-hidden="true"
              className="hidden h-5 w-px bg-border sm:block"
            />
            <time
              className="hidden font-medium tabular-nums sm:inline"
              dateTime={now.toISOString()}
            >
              {formatHeaderTime(now, timezone)}
            </time>
          </div>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-[1484px] md:grid-cols-[196px_minmax(0,1fr)]">
        <aside className="hidden min-h-[calc(100vh-68px)] border-r border-border px-3 py-8 md:flex md:flex-col">
          <PrimaryNavigation />
          <p className="mt-auto border-t border-border px-3 pt-6 text-sm leading-6 text-muted-foreground">
            让好工作
            <br />
            找到对的人
          </p>
        </aside>
        {children}
      </div>
    </div>
  );
}

function MobileNavigation() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <button
          aria-label="打开主导航"
          className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
          type="button"
        >
          <Menu aria-hidden="true" className="size-5" />
        </button>
      </SheetTrigger>
      <SheetContent aria-describedby={undefined}>
        <div className="mb-8 flex items-center gap-2 pr-10 text-lg font-extrabold">
          <FileText aria-hidden="true" className="size-5 text-primary" />
          JOBAGENT
        </div>
        <PrimaryNavigation mobile />
      </SheetContent>
    </Sheet>
  );
}

function PrimaryNavigation({ mobile = false }: { mobile?: boolean }) {
  return (
    <nav aria-label="主导航">
      <ul className="space-y-1.5">
        {navigation.map(({ label, icon: Icon, current }) => (
          <li key={label}>
            {current ? (
              <CurrentNavigationLink
                icon={Icon}
                label={label}
                mobile={mobile}
              />
            ) : (
              <span
                aria-disabled="true"
                className="flex h-12 cursor-not-allowed items-center gap-3 rounded-lg px-3.5 font-medium text-muted-foreground/75"
                title={`${label} · 计划中`}
              >
                <Icon aria-hidden="true" className="size-5" strokeWidth={1.8} />
                <span>{label}</span>
                <span className="ml-auto text-[10px] font-medium">计划中</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </nav>
  );
}

function CurrentNavigationLink({
  icon: Icon,
  label,
  mobile,
}: {
  icon: (typeof navigation)[number]["icon"];
  label: string;
  mobile: boolean;
}) {
  const link = (
    <a
      aria-current="page"
      className="flex h-12 items-center gap-3 rounded-lg bg-primary/9 px-3.5 font-semibold text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      href="/app/"
    >
      <Icon aria-hidden="true" className="size-5" strokeWidth={2} />
      {label}
    </a>
  );
  return mobile ? <SheetClose asChild>{link}</SheetClose> : link;
}

function SystemHealth({ health }: { health: HealthSnapshot }) {
  const ready = health.live === "alive" && health.ready === "ready";
  const processOnly = health.live === "alive" && health.ready !== "ready";
  return (
    <Badge
      className={cn(
        "border-0 px-2.5",
        processOnly && "text-attention-foreground",
      )}
      variant={ready ? "success" : processOnly ? "attention" : "neutral"}
    >
      <span
        aria-hidden="true"
        className={cn(
          "size-2 rounded-full bg-muted-foreground",
          ready && "bg-success",
          processOnly && "bg-attention",
        )}
      />
      {ready ? "系统正常" : processOnly ? "数据库未就绪" : "连接检查中"}
    </Badge>
  );
}

function formatHeaderTime(value: Date, timezone: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: timezone,
  }).format(value);
}
