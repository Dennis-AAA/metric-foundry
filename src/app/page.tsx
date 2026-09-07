import Link from "next/link";
import { BookOpen } from "lucide-react";

import { Legend } from "@/components/dashboard/legend";
import { MatrixTable } from "@/components/dashboard/matrix-table";
import { MobileCards } from "@/components/dashboard/mobile-cards";
import { StatusBar } from "@/components/dashboard/status-bar";
import { Button } from "@/components/ui/button";
import { listHistoryDates, loadSnapshot, loadTimeline } from "@/lib/data";

export const dynamic = "force-dynamic";

function refreshEnabled(): boolean {
  if (process.env.MACROVOL_ALLOW_REFRESH === "0") return false;
  if (process.env.VERCEL) return false;
  return true;
}

export default async function Page() {
  const [snapshot, timeline, history] = await Promise.all([loadSnapshot(), loadTimeline(), listHistoryDates()]);

  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            方向偏好 <span className="text-slate-400">×</span> 波动率偏好
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            六大类资产的 DELTA（短线 1–4 周 / 长线 1–3 月）与 VEGA · SKEW · GAMMA · VOL 体制信号矩阵。 数据来自 Yahoo Finance 期货日线与 ETF 期权链、CBOE 波动率指数、CFTC 持仓报告，全部为公开免费来源。
          </p>
        </div>
        <Button variant="outline" size="sm" render={<Link href="/methodology" />}>
          <BookOpen />
          方法说明与复现
        </Button>
      </header>

      {!snapshot ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <h2 className="text-lg font-semibold text-slate-800">还没有数据快照</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
            运行一次信号引擎生成 <code className="rounded bg-slate-100 px-1">data/latest.json</code>，页面会自动读取：
          </p>
          <pre className="mx-auto mt-4 w-fit rounded-md bg-slate-900 px-4 py-3 text-left text-xs text-slate-100">
            {`uv pip install -e ./engine\npython -m macrovol.cli run`}
          </pre>
        </div>
      ) : (
        <>
          <StatusBar snapshot={snapshot} historyCount={history.length} refreshEnabled={refreshEnabled()} />
          <div className="hidden md:block">
            <MatrixTable snapshot={snapshot} timeline={timeline} />
          </div>
          <div className="md:hidden">
            <MobileCards snapshot={snapshot} timeline={timeline} />
          </div>
          <div className="grid gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 shadow-sm sm:grid-cols-2">
            <div>
              <span className="font-semibold text-slate-800">短线：</span>
              {snapshot.notes.short}
            </div>
            <div className="sm:border-l sm:border-slate-200 sm:pl-4">
              <span className="font-semibold text-slate-800">长线：</span>
              {snapshot.notes.long}
            </div>
          </div>
          <Legend />
        </>
      )}
    </main>
  );
}
