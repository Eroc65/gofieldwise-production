import { useEffect, useState } from "react";

import {
  createMarketingImageCustomPack,
  deleteMarketingImageCustomPack,
  generateMarketingImage,
  listMarketingImageCampaignPacks,
  listMarketingImageChannels,
  listMarketingImageCustomPacks,
  listMarketingImageTemplates,
  listMarketingImageTradeTemplates,
  login,
} from "../lib/api";

export default function MarketingAIPage() {
  const [token, setToken] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [templates, setTemplates] = useState([]);
  const [channels, setChannels] = useState([]);
  const [tradeTemplates, setTradeTemplates] = useState([]);
  const [campaignPacks, setCampaignPacks] = useState([]);
  const [customPacks, setCustomPacks] = useState([]);
  const [customPackName, setCustomPackName] = useState("");
  const [selectedPack, setSelectedPack] = useState("");
  const [templateCode, setTemplateCode] = useState("social_promo");
  const [channelCode, setChannelCode] = useState("instagram_feed");
  const [tradeCode, setTradeCode] = useState("general_home_services");
  const [businessName, setBusinessName] = useState("FieldWise");
  const [serviceType, setServiceType] = useState("HVAC");
  const [offerText, setOfferText] = useState("Spring Tune-Up Special - Save 20% This Week");
  const [ctaText, setCtaText] = useState("Book Today");
  const [primaryColor, setPrimaryColor] = useState("#0f172a");
  const [prompt, setPrompt] = useState("Use a clean modern layout with bold headline, trust-focused visual style, and a clear CTA button area.");
  const [size, setSize] = useState("1024x1024");
  const [quality, setQuality] = useState("high");
  const [imageData, setImageData] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState("");

  useEffect(() => {
    const savedToken = window.localStorage.getItem("fdp.dispatch.token") || "";
    const savedEmail = window.localStorage.getItem("fdp.dispatch.email") || "";
    if (savedToken) setToken(savedToken);
    if (savedEmail) setAuthEmail(savedEmail);
  }, []);

  async function withBusy(fn) {
    setBusy(true);
    setError("");
    setResult("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onLogin() {
    await withBusy(async () => {
      const response = await login({ email: authEmail, password: authPassword });
      setToken(response.access_token);
      window.localStorage.setItem("fdp.dispatch.token", response.access_token);
      window.localStorage.setItem("fdp.dispatch.email", authEmail);

      const [templateRows, channelRows, tradeRows, packRows, customPackRows] = await Promise.all([
        listMarketingImageTemplates({ token: response.access_token }),
        listMarketingImageChannels({ token: response.access_token }),
        listMarketingImageTradeTemplates({ token: response.access_token }),
        listMarketingImageCampaignPacks({ token: response.access_token }),
        listMarketingImageCustomPacks({ token: response.access_token }),
      ]);
      setTemplates(Array.isArray(templateRows) ? templateRows : []);
      setChannels(Array.isArray(channelRows) ? channelRows : []);
      setTradeTemplates(Array.isArray(tradeRows) ? tradeRows : []);
      setCampaignPacks(Array.isArray(packRows) ? packRows : []);
      setCustomPacks(Array.isArray(customPackRows) ? customPackRows : []);

      setResult("Operator session ready.");
    });
  }

  useEffect(() => {
    if (!token) {
      return;
    }
    let cancelled = false;
    async function loadTemplates() {
      try {
        const [templateRows, channelRows, tradeRows, packRows, customPackRows] = await Promise.all([
          listMarketingImageTemplates({ token }),
          listMarketingImageChannels({ token }),
          listMarketingImageTradeTemplates({ token }),
          listMarketingImageCampaignPacks({ token }),
          listMarketingImageCustomPacks({ token }),
        ]);
        if (!cancelled) {
          setTemplates(Array.isArray(templateRows) ? templateRows : []);
          setChannels(Array.isArray(channelRows) ? channelRows : []);
          setTradeTemplates(Array.isArray(tradeRows) ? tradeRows : []);
          setCampaignPacks(Array.isArray(packRows) ? packRows : []);
          setCustomPacks(Array.isArray(customPackRows) ? customPackRows : []);
        }
      } catch {
        if (!cancelled) {
          setTemplates([]);
          setChannels([]);
          setTradeTemplates([]);
          setCampaignPacks([]);
          setCustomPacks([]);
        }
      }
    }
    void loadTemplates();
    return () => {
      cancelled = true;
    };
  }, [token]);

  function applyTemplateDefaults(code) {
    setTemplateCode(code);
    if (code === "seasonal_offer") {
      setSize("1536x1024");
      setOfferText("Limited Seasonal Offer - Save Before It Ends");
      setCtaText("Claim Offer");
    } else if (code === "reactivation_offer") {
      setSize("1024x1536");
      setOfferText("We Miss You - Exclusive Return Customer Deal");
      setCtaText("Come Back Today");
    } else if (code === "review_push") {
      setSize("1024x1024");
      setOfferText("Loved Our Service? Share Your 5-Star Review");
      setCtaText("Leave Review");
    } else {
      setSize("1024x1024");
      setOfferText("Spring Tune-Up Special - Save 20% This Week");
      setCtaText("Book Today");
    }
  }

  function applyChannelDefaults(code) {
    setChannelCode(code);
    if (code === "facebook_landscape") {
      setSize("1536x1024");
    } else if (code === "story_vertical") {
      setSize("1024x1536");
    } else {
      setSize("1024x1024");
    }
  }

  function applyCampaignPack(code) {
    setSelectedPack(code);
    const pack = [...(campaignPacks || []), ...(customPacks || [])].find((item) => item.code === code);
    if (!pack) {
      return;
    }
    setTemplateCode(pack.template_code);
    setChannelCode(pack.channel_code);
    setTradeCode(pack.trade_code);
    setServiceType(pack.service_type);
    setOfferText(pack.offer_text);
    setCtaText(pack.cta_text);
    setPrimaryColor(pack.primary_color);
    setPrompt(pack.prompt);
    if (pack.channel_code === "facebook_landscape") {
      setSize("1536x1024");
    } else if (pack.channel_code === "story_vertical") {
      setSize("1024x1536");
    } else {
      setSize("1024x1024");
    }
  }

  async function saveCustomPack() {
    const name = customPackName.trim();
    if (!name) {
      setError("Custom pack name is required.");
      return;
    }

    await withBusy(async () => {
      const created = await createMarketingImageCustomPack({
        token,
        payload: {
          name,
          description: "Custom saved preset",
          template_code: templateCode,
          channel_code: channelCode,
          trade_code: tradeCode,
          service_type: serviceType,
          offer_text: offerText,
          cta_text: ctaText,
          primary_color: primaryColor,
          prompt,
        },
      });
      setCustomPacks((current) => [created, ...(Array.isArray(current) ? current : [])]);
      setCustomPackName("");
      setResult(`Saved custom pack: ${name}`);
    });
  }

  async function deleteSelectedCustomPack() {
    if (!selectedPack.startsWith("custom_")) {
      setError("Select a custom pack to delete.");
      return;
    }
    const pack = (customPacks || []).find((item) => item.code === selectedPack);
    if (!pack || !pack.id) {
      setError("Custom pack not found.");
      return;
    }
    await withBusy(async () => {
      await deleteMarketingImageCustomPack({ token, packId: pack.id });
      setCustomPacks((current) => (Array.isArray(current) ? current.filter((item) => item.id !== pack.id) : []));
      setSelectedPack("");
      setResult("Custom pack deleted.");
    });
  }

  async function onGenerate() {
    await withBusy(async () => {
      if (!prompt.trim()) {
        throw new Error("Prompt is required.");
      }
      const out = await generateMarketingImage({
        token,
        prompt,
        size,
        quality,
        templateCode,
        channelCode,
        tradeCode,
        businessName,
        serviceType,
        offerText,
        ctaText,
        primaryColor,
      });
      setImageData(`data:${out.mime_type};base64,${out.image_base64}`);
      setResult("Marketing image generated.");
    });
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">AI Marketing Studio</p>
        <h1>Generate Campaign Images Powered By AI</h1>
        <p>Create social-ready creative for seasonal promos, follow-up campaigns, and website offers in seconds.</p>
        <div className="hero-actions">
          <a className="ghost-link" href="/">Marketing Site</a>
          <a className="ghost-link" href="/platform">Platform Console</a>
        </div>
      </section>

      <section className="dispatch-card">
        <h2>Operator Login</h2>
        <div className="form-grid">
          <label>
            Email
            <input value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} />
          </label>
        </div>
        <div className="actions">
          <button type="button" onClick={onLogin} disabled={busy}>Login</button>
        </div>
      </section>

      <section className="dispatch-card">
        <h2>Generate Image</h2>
        <div className="form-grid">
          <label className="span-2">
            Campaign Pack
            <select value={selectedPack} onChange={(e) => applyCampaignPack(e.target.value)}>
              <option value="">Select a campaign pack</option>
              {(campaignPacks || []).length > 0 ? (
                <optgroup label="Built-in packs">
                  {(campaignPacks || []).map((item) => (
                    <option key={item.code} value={item.code}>{item.name}</option>
                  ))}
                </optgroup>
              ) : null}
              {(customPacks || []).length > 0 ? (
                <optgroup label="Your custom packs">
                  {(customPacks || []).map((item) => (
                    <option key={item.code} value={item.code}>{item.name}</option>
                  ))}
                </optgroup>
              ) : null}
            </select>
          </label>
          <label>
            Save Current As
            <input value={customPackName} onChange={(e) => setCustomPackName(e.target.value)} placeholder="My Summer Promo Pack" />
          </label>
          <div className="actions" style={{ alignItems: "end" }}>
            <button type="button" onClick={saveCustomPack} disabled={!token || busy}>Save Custom Pack</button>
            <button type="button" onClick={deleteSelectedCustomPack} disabled={!token || busy}>Delete Selected Custom Pack</button>
          </div>
          <label>
            Template
            <select value={templateCode} onChange={(e) => applyTemplateDefaults(e.target.value)}>
              {(templates.length ? templates : [
                { code: "social_promo", name: "Social Promo" },
                { code: "seasonal_offer", name: "Seasonal Offer" },
                { code: "review_push", name: "Review Push" },
                { code: "reactivation_offer", name: "Reactivation Offer" },
              ]).map((item) => (
                <option key={item.code} value={item.code}>{item.name}</option>
              ))}
            </select>
          </label>
          <label>
            Channel Preset
            <select value={channelCode} onChange={(e) => applyChannelDefaults(e.target.value)}>
              {(channels.length ? channels : [
                { code: "instagram_feed", name: "Instagram Feed" },
                { code: "facebook_landscape", name: "Facebook Landscape" },
                { code: "story_vertical", name: "Story Vertical" },
              ]).map((item) => (
                <option key={item.code} value={item.code}>{item.name}</option>
              ))}
            </select>
          </label>
          <label>
            Trade Prompt Template
            <select value={tradeCode} onChange={(e) => setTradeCode(e.target.value)}>
              {(tradeTemplates.length ? tradeTemplates : [
                { code: "general_home_services", name: "General Home Services" },
                { code: "hvac", name: "HVAC" },
                { code: "plumbing", name: "Plumbing" },
                { code: "electrical", name: "Electrical" },
              ]).map((item) => (
                <option key={item.code} value={item.code}>{item.name}</option>
              ))}
            </select>
          </label>
          <label>
            Business Name
            <input value={businessName} onChange={(e) => setBusinessName(e.target.value)} />
          </label>
          <label>
            Service Type
            <input value={serviceType} onChange={(e) => setServiceType(e.target.value)} />
          </label>
          <label>
            Offer Text
            <input value={offerText} onChange={(e) => setOfferText(e.target.value)} />
          </label>
          <label>
            CTA Text
            <input value={ctaText} onChange={(e) => setCtaText(e.target.value)} />
          </label>
          <label>
            Primary Color
            <input value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} />
          </label>
          <label className="span-2">
            Prompt
            <textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </label>
          <label>
            Size
            <select value={size} onChange={(e) => setSize(e.target.value)}>
              <option value="1024x1024">1024x1024</option>
              <option value="1536x1024">1536x1024</option>
              <option value="1024x1536">1024x1536</option>
            </select>
          </label>
          <label>
            Quality
            <select value={quality} onChange={(e) => setQuality(e.target.value)}>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
          </label>
        </div>
        <div className="actions">
          <button type="button" onClick={onGenerate} disabled={!token || busy}>Generate Marketing Image</button>
        </div>
        {error ? <p className="submit-error">{error}</p> : null}
        {result ? <p className="submit-note">{result}</p> : null}
      </section>

      {imageData ? (
        <section className="dispatch-card">
          <h2>Preview</h2>
          <img src={imageData} alt="Generated marketing creative" style={{ width: "100%", maxWidth: 640, borderRadius: 12 }} />
          <div className="actions">
            <a className="ghost-link" href={imageData} download="marketing-image.png">Download PNG</a>
          </div>
        </section>
      ) : null}
    </main>
  );
}
