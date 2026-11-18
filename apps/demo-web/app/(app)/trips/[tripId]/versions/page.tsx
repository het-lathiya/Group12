import { Icon } from "@/components/ui";
import { versions } from "@/lib/data";

// TODO: GET/POST /api/v1/trips/{id}/versions and POST .../versions/{version_id}/restore
export default function Versions() {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between">
        <div><h2 className="text-xl font-bold">Version history</h2><p className="text-sm text-muted">Every change is saved. Restore any version.</p></div>
        <button className="btn-primary"><Icon name="bookmark_add" />Save current</button>
      </div>
      <ol className="relative mt-6 space-y-3 border-l-2 border-dashed border-line pl-6">
        {versions.map((v) => (
          <li key={v.id} className="card relative flex flex-wrap items-center gap-4 p-4">
            <span className={`absolute -left-[33px] top-6 h-3 w-3 rounded-full ring-4 ring-canvas ${v.current ? "bg-coral" : "bg-line"}`} />
            <span className={`grid h-10 w-10 place-items-center rounded-xl ${v.by === "TripBook AI" ? "bg-coral-wash text-coral" : "bg-sky text-slate"}`}>
              <Icon name={v.by === "TripBook AI" ? "auto_awesome" : "person"} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{v.label}</p>
              <p className="text-xs text-muted">{v.by} • {v.when}</p>
            </div>
            {v.current ? <span className="badge-mint">Current</span> : (
              <div className="flex gap-2">
                <button className="btn-soft !text-xs">Preview</button>
                <button className="btn-soft !text-xs"><Icon name="restore" className="!text-[15px]" />Restore</button>
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
