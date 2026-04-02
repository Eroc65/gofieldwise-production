import React from 'react';

export default function Home() {
  return (
    <main style={{ padding: 32 }}>
      <h1>AI Ops Hub Operator Console</h1>
      <ul>
        <li>Task Inbox</li>
        <li>Approvals Queue</li>
        <li>Live Run Log</li>
        <li>Artifacts Panel</li>
        <li>Credentials Status</li>
        <li>Agent Health</li>
        <li>"Ask the Operator" Chat Box</li>
      </ul>
      <p>This is the shell for the operator dashboard. Features will be implemented incrementally.</p>
    </main>
  );
}
