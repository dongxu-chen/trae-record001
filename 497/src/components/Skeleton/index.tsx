import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-lg bg-slate-700/50',
        className
      )}
    />
  );
}

export function ChartSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-16" />
          <Skeleton className="h-9 w-16" />
          <Skeleton className="h-9 w-16" />
        </div>
      </div>
      <div className="relative h-[480px] rounded-2xl bg-slate-800/60 overflow-hidden">
        <div className="absolute inset-0 flex items-end justify-around px-8 pb-12">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="w-12 bg-slate-700/60 rounded-t-lg animate-pulse"
              style={{
                height: `${30 + Math.random() * 60}%`,
                animationDelay: `${i * 0.1}s`,
              }}
            />
          ))}
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-12 border-t border-slate-700/50 flex justify-around items-center">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-3 w-12" />
          ))}
        </div>
        <div className="absolute top-4 left-4 w-16 h-32 flex flex-col justify-between">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-3 w-12" />
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-cyan-500/50 animate-pulse" />
        <Skeleton className="h-4 w-64" />
      </div>
    </div>
  );
}

export function StatusPanelSkeleton() {
  return (
    <div className="space-y-5">
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/50">
        <Skeleton className="h-6 w-24 mb-4" />
        <div className="grid grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-900/40 rounded-xl p-4 space-y-2">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <Skeleton className="h-7 w-20" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/50">
        <Skeleton className="h-6 w-24 mb-4" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
              <div className="flex items-center gap-3">
                <Skeleton className="h-5 w-5" />
                <Skeleton className="h-5 w-20" />
              </div>
              <Skeleton className="h-5 w-16" />
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <Skeleton className="h-12 w-full rounded-xl" />
        </div>
      </div>

      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/50">
        <Skeleton className="h-6 w-24 mb-4" />
        <div className="space-y-2 max-h-64">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
              <div className="flex items-center gap-3">
                <Skeleton className="h-6 w-6 rounded-full" />
                <Skeleton className="h-5 w-24" />
              </div>
              <Skeleton className="h-5 w-16" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function BreadcrumbSkeleton() {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-9 w-20 rounded-xl" />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Skeleton className="h-11 w-24 rounded-xl" />
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-11 w-28 rounded-xl" />
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-slate-700/50">
        <div className="flex items-center gap-4 mb-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-28" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-16" />
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-6 w-12 rounded-md" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="relative z-10 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="text-center mb-10">
          <div className="flex justify-center mb-6">
            <Skeleton className="h-9 w-48 rounded-full" />
          </div>
          <Skeleton className="h-14 w-96 mx-auto mb-4" />
          <Skeleton className="h-6 w-[500px] mx-auto mb-8" />
          <div className="flex flex-wrap justify-center gap-4">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-56 rounded-xl" />
            ))}
          </div>
        </header>

        <main className="space-y-6">
          <BreadcrumbSkeleton />
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className="bg-slate-800/60 rounded-2xl p-6 border border-slate-700/50 h-full">
                <ChartSkeleton />
              </div>
            </div>
            <div className="lg:col-span-1">
              <StatusPanelSkeleton />
            </div>
          </div>
          <div className="bg-slate-800/40 rounded-2xl p-6 border border-slate-700/50">
            <Skeleton className="h-6 w-24 mb-4" />
            <div className="grid md:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex gap-4">
                  <Skeleton className="h-10 w-12" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-5 w-24" />
                    <Skeleton className="h-4 w-full" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
