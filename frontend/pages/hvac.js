import IndustryPage from "../components/industry-page";

export default function HvacPage() {
  return (
    <IndustryPage
      industryLabel="HVAC Teams"
      slug="hvac"
      heroTagline="AI Field Service Management for HVAC Shops"
      description="GoFieldwise helps HVAC businesses answer calls faster, schedule tune-ups efficiently, and keep every job moving from dispatch to payment."
      ctaLabel="Try HVAC Demo"
      operatorPromise="HVAC demand swings hard: no-cool emergencies, tune-up campaigns, filter reminders, replacement leads, and maintenance plans all need different handling."
      scenario={{
        title: "No cooling during a heat wave",
        body: "Adrian captures system type, thermostat symptoms, age of unit, pets or elderly occupants, and whether the customer is a maintenance member.",
        urgency: "Heat-priority dispatch",
        outcome: "Service call gets routed with symptoms, equipment context, and membership status.",
      }}
      intakeFields={[
        { name: "System", example: "Split AC, outdoor unit running, indoor air warm" },
        { name: "Customer risk", example: "Elderly parent in the home" },
        { name: "Equipment age", example: "About 12 years old" },
        { name: "Plan status", example: "Maintenance member, priority scheduling" },
      ]}
      differentiators={[
        {
          label: "Seasonality",
          title: "Peak season calls cannot wait",
          text: "Adrian keeps the phone covered during heat waves and cold snaps when your team is already maxed out.",
        },
        {
          label: "Revenue",
          title: "Tune-ups become repeatable campaigns",
          text: "Maintenance follow-ups, filter reminders, and seasonal reactivation can run without manual lists.",
        },
        {
          label: "Replacement",
          title: "A repair call can become a quote opportunity",
          text: "Age, symptoms, and repeat issues get captured so replacement leads are not missed.",
        },
      ]}
      workflow={{
        title: "From no-cool call to scheduled HVAC revenue.",
        steps: [
          { title: "Answer", text: "Adrian picks up during rush periods and asks HVAC-specific symptom questions." },
          { title: "Prioritize", text: "No heat, no cooling, member status, and vulnerable occupants shape urgency." },
          { title: "Schedule", text: "Tune-ups, repairs, and replacement consults land in the right workflow." },
          { title: "Retain", text: "Service plan, review, and seasonal follow-up messages keep the customer coming back." },
        ],
      }}
      proof={{
        quote: "HVAC shops do not lose because they cannot fix systems. They lose when peak-season phones outrun the office.",
        metric: "Best fit",
        value: "Peak load",
        text: "Adrian absorbs call spikes while your techs stay focused on repairs and installs.",
      }}
      bullets={[
        { title: "Seasonal Rush Ready", text: "Handle no-cool and no-heat spikes with automated triage and scheduling." },
        { title: "Tech Routing", text: "Route by urgency, skill, membership status, and equipment context." },
        { title: "Maintenance Follow-Up", text: "Trigger tune-up reminders, filter campaigns, and service plan nudges automatically." },
      ]}
    />
  );
}
