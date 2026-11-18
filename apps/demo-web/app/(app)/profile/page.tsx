import { Icon } from "@/components/ui";
import { user } from "@/lib/data";

const allStyles = ["Foodie", "Heritage", "Slow travel", "Adventure", "Nightlife", "Nature", "Shopping", "Family"];

export default function Profile() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <p className="label text-coral">Account</p>
      <h1 className="mt-1 text-[32px] font-extrabold tracking-tight">Profile</h1>

      <section className="card mt-6 flex items-center gap-5 p-6">
        <span className="grid h-16 w-16 place-items-center rounded-full bg-slate text-xl font-bold text-white">{user.initials}</span>
        <div className="flex-1"><p className="text-lg font-bold">{user.name}</p><p className="text-sm text-muted">{user.email}</p></div>
        <button className="btn-soft"><Icon name="photo_camera" className="!text-[16px]" />Change photo</button>
      </section>

      {/* TODO: GET/PATCH /api/v1/me */}
      <form className="card mt-5 space-y-5 p-6">
        <h2 className="text-lg font-semibold">Details</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label><span className="label text-muted">Display name</span><input className="input mt-1.5" defaultValue={user.name} /></label>
          <label><span className="label text-muted">Home city</span><input className="input mt-1.5" defaultValue={user.home} /></label>
          <label><span className="label text-muted">Currency</span><select className="input mt-1.5"><option>INR ₹</option><option>USD $</option><option>EUR €</option></select></label>
          <label><span className="label text-muted">Default budget</span><select className="input mt-1.5"><option>Moderate</option><option>Budget</option><option>Luxury</option></select></label>
        </div>
        <div>
          <span className="label text-muted">Travel style</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {allStyles.map((s) => <span key={s} className={`chip cursor-pointer ${user.style.includes(s) ? "chip-active" : ""}`}>{s}</span>)}
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-hair pt-5">
          <button type="button" className="btn-soft">Cancel</button>
          <button type="button" className="btn-primary">Save changes</button>
        </div>
      </form>

      <section className="card mt-5 flex items-center justify-between p-6">
        <div><p className="font-semibold">Sign out</p><p className="text-sm text-muted">You can sign back in anytime.</p></div>
        <a href="/sign-in" className="btn-soft"><Icon name="logout" className="!text-[16px]" />Sign out</a>
      </section>
    </main>
  );
}
