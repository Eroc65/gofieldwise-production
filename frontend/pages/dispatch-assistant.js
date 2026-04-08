import DispatchAssistant from "../components/DispatchAssistant";

export default function DispatchAssistantPage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Operations</p>
        <h1>Dispatch Assistant</h1>
        <p>Operator workflow for scheduling checks, dispatch, and lifecycle progression.</p>
      </section>
      <DispatchAssistant />
    </main>
  );
}
