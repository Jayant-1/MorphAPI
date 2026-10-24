export interface MandiRecord {
  crop_name: string;
  crop_name_marathi: string;
  district: string;
  market_name: string;
  min_price: number;
  max_price: number;
  modal_price: number;
  unit: string;
  arrival_quantity: string;
  last_updated: string;
}

export const SAMPLE_MANDI_DATA: MandiRecord[] = [
  {
    crop_name: "Onion (कांदा)",
    crop_name_marathi: "लाल कांदा (Red Onion)",
    district: "Nashik (नाशिक)",
    market_name: "Lasalgaon APMC (लासलगाव)",
    min_price: 1850,
    max_price: 2620,
    modal_price: 2450,
    unit: "₹ / Quintal",
    arrival_quantity: "14,800 Quintals",
    last_updated: "24-Oct-2026 18:30 IST",
  },
  {
    crop_name: "Soybean (सोयाबीन)",
    crop_name_marathi: "पिवळी सोयाबीन (Yellow Soybean)",
    district: "Latur (लातूर)",
    market_name: "Latur Krishi Mandi (लातूर मुख्य)",
    min_price: 4300,
    max_price: 4950,
    modal_price: 4820,
    unit: "₹ / Quintal",
    arrival_quantity: "9,240 Quintals",
    last_updated: "24-Oct-2026 17:45 IST",
  },
  {
    crop_name: "Cotton (कापूस)",
    crop_name_marathi: "मध्यम स्टेपल (Medium Staple)",
    district: "Akola (अकोला)",
    market_name: "Akola APMC (अकोला)",
    min_price: 6700,
    max_price: 7450,
    modal_price: 7280,
    unit: "₹ / Quintal",
    arrival_quantity: "6,100 Quintals",
    last_updated: "24-Oct-2026 19:10 IST",
  },
  {
    crop_name: "Pomegranate (डाळिंब)",
    crop_name_marathi: "भगवा डाळिंब (Bhagwa)",
    district: "Solapur (सोलापूर)",
    market_name: "Pandharpur Mandi (पंढरपूर)",
    min_price: 5500,
    max_price: 11200,
    modal_price: 9400,
    unit: "₹ / Quintal",
    arrival_quantity: "3,400 Quintals",
    last_updated: "24-Oct-2026 16:50 IST",
  },
];

export interface TraceStep {
  id: number;
  timeMs: number;
  label: string;
  badge: string;
  badgeColor: "rose" | "amber" | "cyan" | "emerald";
  title: string;
  description: string;
  details: {
    key: string;
    value: string;
  }[];
  codeSnippet?: string;
}

export const HEALER_TRACE_STEPS: TraceStep[] = [
  {
    id: 1,
    timeMs: 410,
    label: "00:00.410",
    badge: "DETECT CRASH",
    badgeColor: "rose",
    title: "Playwright Caught Selector Timeout",
    description:
      "Target portal updated CSS. Cached selector `table#mandi-data > tbody > tr` resolved to 0 nodes. Client connection held in flight.",
    details: [
      { key: "Target Endpoint", value: "https://msamb.com/prices/nashik" },
      { key: "Exception", value: "TimeoutError (3000ms exceeded)" },
      { key: "Client Connection", value: "HELD OPEN (No 500 error)" },
    ],
    codeSnippet: `try:
    rows = await page.locator("table#mandi-data > tbody > tr").all()
except PlaywrightTimeoutError as err:
    # Autonomous Circuit Catch: Hold connection, trigger Healer
    logger.warning("Cached selector broke on msamb.com! Entering heal loop.")`,
  },
  {
    id: 2,
    timeMs: 680,
    label: "00:00.680",
    badge: "TOKEN MINIFIER",
    badgeColor: "amber",
    title: "BS4 AST Stripper -89.4% Compression",
    description:
      "High-res viewport captured. Stripped script tags, inline stylesheets, tracking iframes, and redundant SVG vectors before AI dispatch.",
    details: [
      { key: "Original DOM Size", value: "1,428.4 KB (185,000 tokens)" },
      { key: "Minified AST Payload", value: "15.2 KB (1,920 tokens)" },
      { key: "Token Cost Saved", value: "-89.4% ($0.0028 vs $0.048)" },
    ],
    codeSnippet: `soup = BeautifulSoup(raw_html, "lxml")
for tag in soup(["script", "style", "svg", "iframe", "noscript"]):
    tag.decompose()
minified_html = soup.prettify()  # 15.2 KB sent to Vision AI`,
  },
  {
    id: 3,
    timeMs: 1820,
    label: "00:01.820",
    badge: "VISION AI DISPATCH",
    badgeColor: "cyan",
    title: "Multimodal AI Proposes Structural Hypothesis",
    description:
      "NVIDIA NIM (Llama 3.1 Vision / DeepSeek) inspects page screenshot + AST with MandiPrice Pydantic schema and Marathi semantic text anchors.",
    details: [
      { key: "Model Provider", value: "NVIDIA NIM (meta/llama-3.1-70b-instruct)" },
      { key: "Semantic Match", value: "'कांदा', 'दर', 'क्विंटल' mapped to card grid" },
      { key: "Proposed Selector", value: "div.grid-layout > div.price-card" },
    ],
    codeSnippet: `Hypothesis:
Portal migrated from <table> to modern Tailwind card grid.
- Crop: div.price-card h3.crop-title
- Price: div.price-card span.rate-value
- District: div.price-card span.badge-district`,
  },
  {
    id: 4,
    timeMs: 2750,
    label: "00:02.750",
    badge: "PLAYWRIGHT VERIFY",
    badgeColor: "emerald",
    title: "Deterministic Live DOM Verification",
    description:
      "Playwright runs proposed selector against live session. Pydantic validator checks 4/4 records match strict types: ints, strings, timestamps.",
    details: [
      { key: "Nodes Evaluated", value: "4 matched records" },
      { key: "Pydantic Schema", value: "100% strict type pass" },
      { key: "Sanity Check", value: "Modal price ₹2,450 within historic ±15% band" },
    ],
    codeSnippet: `class MandiPrice(BaseModel):
    crop_name: str
    price_per_quintal: int
    district: str

# Validated: MandiPrice(crop_name='कांदा', price_per_quintal=2450, district='नाशिक')
# Deterministic Validator: APPROVED FOR PROMOTION`,
  },
  {
    id: 5,
    timeMs: 3180,
    label: "00:03.180",
    badge: "PATCH & RETURN",
    badgeColor: "emerald",
    title: "Registry Hot-Patched & HTTP 200 Returned",
    description:
      "SQLite updated (v1 -> v2). Client HTTP request completes with 200 OK. WhatsApp farmer bot receives data with 0 downtime recorded.",
    details: [
      { key: "Status Code", value: "HTTP 200 OK" },
      { key: "Total Healing Latency", value: "3,180ms" },
      { key: "Downtime Recorded", value: "0.00 seconds" },
      { key: "Next Execution", value: "Fast Path ~410ms (cached selector)" },
    ],
    codeSnippet: `UPDATE integrations 
SET active_version_id = 'ver_mandi_v2', current_version = 2
WHERE slug = 'maharashtra-mandi-prices';

# Return HTTP 200 OK to awaiting client with clean JSON`,
  },
];
