import Head from "next/head";
import { useRouter } from "next/router";

import SiteNav from "../components/SiteNav";
import "../styles/globals.css";

export default function App({ Component, pageProps }) {
  const router = useRouter();
  const baseUrl = "https://gofieldwise.com";
  const path = (router.asPath || "/").split("?")[0].split("#")[0];
  const currentUrl = `${baseUrl}${path}`;

  const defaultMeta = {
    title: "GoFieldwise - AI Field Service Management for Home Service Businesses",
    description:
      "Never miss a customer. Automate every job-from first call to paid invoice. AI-powered scheduling, dispatch, and invoicing for contractors.",
    image: `${baseUrl}/og-image.png`,
  };

  const meta = {
    title: pageProps?.meta?.title || defaultMeta.title,
    description: pageProps?.meta?.description || defaultMeta.description,
    image: pageProps?.meta?.image || defaultMeta.image,
  };

  const softwareSchema = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "GoFieldwise",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description: "AI-powered field service management software for home service businesses",
    url: baseUrl,
    publisher: {
      "@type": "Organization",
      name: "GoFieldwise",
      url: baseUrl,
    },
    offers: {
      "@type": "Offer",
      price: "200",
      priceCurrency: "USD",
    },
  };

  return (
    <>
      <Head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="robots" content="index, follow" />
        <meta name="language" content="English" />

        <title>{meta.title}</title>
        <meta name="description" content={meta.description} />

        <meta property="og:type" content="website" />
        <meta property="og:url" content={currentUrl} />
        <meta property="og:title" content={meta.title} />
        <meta property="og:description" content={meta.description} />
        <meta property="og:image" content={meta.image} />
        <meta property="og:site_name" content="GoFieldwise" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={meta.title} />
        <meta name="twitter:description" content={meta.description} />
        <meta name="twitter:image" content={meta.image} />

        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareSchema) }}
        />

        <link rel="icon" href="/favicon.ico" />
        <link rel="canonical" href={currentUrl} />
      </Head>

      <SiteNav />
      <Component {...pageProps} />
    </>
  );
}
