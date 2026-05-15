/**
 * Twilio voice webhook for GoFieldWise Connect.
 * Called by Twilio when a call arrives at (602) 932-0967.
 * Returns TwiML that bridges the call to the Retell AI receptionist.
 */
export default function handler(req, res) {
  if (req.method !== 'POST' && req.method !== 'GET') {
    res.status(405).end('Method Not Allowed');
    return;
  }

  const agentId =
    process.env.RETELL_DEMO_AGENT_ID ||
    'agent_08985605972e2e1b5d8a92dd52';

  const sipUri = 'sip:' + agentId + '@sip.retellai.com;transport=tls';

  const twiml = '<?xml version="1.0" encoding="UTF-8"?>' +
    '<Response>' +
    '<Dial>' +
    '<Sip>' + sipUri + '</Sip>' +
    '</Dial>' +
    '</Response>';

  res.setHeader('Content-Type', 'text/xml; charset=utf-8');
  res.status(200).send(twiml);
}
