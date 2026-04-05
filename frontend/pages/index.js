import DispatchAssistant from "../components/DispatchAssistant";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">FrontDesk Pro</p>
        <h1>Dispatch With Less Chaos</h1>
        <p>
          Use live conflict checks and next-slot suggestions to dispatch jobs faster while respecting
          business-hour windows.
        </p>
      </section>

      <DispatchAssistant />
    </main>
  );
}
