export default function Loading() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          className="h-20 animate-pulse rounded-lg border border-border bg-muted-background"
        />
      ))}
    </div>
  );
}
