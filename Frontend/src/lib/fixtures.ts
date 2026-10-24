import { EndpointDefinition, FieldDefinition, PageMetadata, PipelineStep, LogEntry } from "./types";

export interface DemoFixture {
  id: string;
  name: string;
  category: string;
  url: string;
  prompt: string;
  pageMetadata: PageMetadata;
  steps: PipelineStep[];
  discoveredFields: FieldDefinition[];
  endpoints: EndpointDefinition[];
  logs: LogEntry[];
  approvalMessage?: string;
  errorMessage?: string;
  testFailureEndpointId?: string;
}

export const DEMO_FIXTURES: Record<string, DemoFixture> = {
  multi_endpoint_catalog: {
    id: "multi_endpoint_catalog",
    name: "E-Commerce Catalogue (Multiple Endpoints)",
    category: "E-Commerce",
    url: "https://books.toscrape.com",
    prompt: "Extract product names, prices, ratings, availability status, categories, and direct product detail links.",
    pageMetadata: {
      url: "https://books.toscrape.com",
      hostname: "books.toscrape.com",
      title: "All products | Books to Scrape - Sandbox",
      httpStatus: 200,
      contentType: "text/html; charset=utf-8",
      elementsInspected: 148,
      captureTime: "2026-10-25 02:18:12 UTC",
      detectedFramework: "HTML5 / Microdata",
    },
    discoveredFields: [
      {
        name: "title",
        type: "string",
        required: true,
        description: "Full title of the publication",
        sampleValue: "A Light in the Attic",
        selector: "article.product_pod h3 a",
        confidence: 0.99,
      },
      {
        name: "price",
        type: "number",
        required: true,
        description: "Current price in GBP",
        sampleValue: 51.77,
        selector: "article.product_pod .price_color",
        confidence: 0.98,
      },
      {
        name: "rating",
        type: "string",
        required: false,
        description: "Star rating classification",
        sampleValue: "Three",
        selector: "article.product_pod p.star-rating",
        confidence: 0.96,
      },
      {
        name: "in_stock",
        type: "boolean",
        required: true,
        description: "Inventory availability indicator",
        sampleValue: true,
        selector: "article.product_pod .instock.availability",
        confidence: 0.99,
      },
      {
        name: "product_url",
        type: "url",
        required: true,
        description: "Canonical link to product detail page",
        sampleValue: "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        selector: "article.product_pod h3 a[href]",
        confidence: 1.0,
      },
    ],
    steps: [
      {
        id: "step_1",
        title: "Request accepted & routing",
        description: "Parameters parsed, SSRF firewall verified target URL",
        status: "success",
        durationMs: 42,
      },
      {
        id: "step_2",
        title: "Headless browser DOM capture",
        description: "Navigated with Playwright Chromium, sanitized 48KB DOM tree",
        status: "success",
        durationMs: 380,
      },
      {
        id: "step_3",
        title: "Semantic schema inference",
        description: "Mapped natural language query into 5 structured fields",
        status: "success",
        durationMs: 290,
      },
      {
        id: "step_4",
        title: "Selector generation & DOM testing",
        description: "Validated CSS selectors against 20 live product containers",
        status: "success",
        durationMs: 195,
      },
      {
        id: "step_5",
        title: "Synthesizing REST & MCP endpoints",
        description: "Generated 4 deterministic REST routes with strict schemas",
        status: "success",
        durationMs: 88,
      },
    ],
    logs: [
      {
        id: "log_1",
        timestamp: "02:18:12.040",
        severity: "info",
        source: "Playwright",
        message: "Initiated Chromium session for https://books.toscrape.com",
      },
      {
        id: "log_2",
        timestamp: "02:18:12.420",
        severity: "info",
        source: "DOMValidator",
        message: "DOM tree loaded (20 products found in container .page-inner)",
      },
      {
        id: "log_3",
        timestamp: "02:18:12.710",
        severity: "info",
        source: "SchemaSynthesis",
        message: "Synthesized candidate selectors for title, price, rating, stock, url",
      },
      {
        id: "log_4",
        timestamp: "02:18:12.905",
        severity: "info",
        source: "DOMValidator",
        message: "Pydantic v2 schema validation: 20/20 elements passed with strict types",
      },
      {
        id: "log_5",
        timestamp: "02:18:12.993",
        severity: "info",
        source: "EndpointGateway",
        message: "Registered 4 endpoints under slug 'books-to-scrape'",
      },
    ],
    endpoints: [
      {
        id: "ep_books_list",
        name: "List Catalog Products",
        method: "GET",
        path: "/api/v1/endpoints/books/products",
        description: "Fetches paginated list of catalog products with title, price, and stock status.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://books.toscrape.com",
        parameters: [
          { name: "page", in: "query", type: "integer", required: false, defaultValue: "1", description: "Page index (1-indexed)" },
          { name: "category", in: "query", type: "string", required: false, description: "Filter by genre slug, e.g. 'travel_2'" },
          { name: "in_stock_only", in: "query", type: "boolean", required: false, defaultValue: "false", description: "Only return products in stock" },
        ],
        responseSchema: {
          type: "object",
          properties: {
            total_items: { type: "integer" },
            page: { type: "integer" },
            items: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  id: { type: "string" },
                  title: { type: "string" },
                  price: { type: "number" },
                  currency: { type: "string" },
                  rating: { type: "string" },
                  in_stock: { type: "boolean" },
                  product_url: { type: "string" },
                },
              },
            },
          },
        },
        sampleResponse: {
          total_items: 20,
          page: 1,
          items: [
            { id: "book_1000", title: "A Light in the Attic", price: 51.77, currency: "GBP", rating: "Three", in_stock: true, product_url: "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" },
            { id: "book_999", title: "Tipping the Velvet", price: 53.74, currency: "GBP", rating: "One", in_stock: true, product_url: "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html" },
            { id: "book_998", title: "Soumission", price: 50.10, currency: "GBP", rating: "One", in_stock: true, product_url: "https://books.toscrape.com/catalogue/soumission_998/index.html" },
            { id: "book_997", title: "Sharp Objects", price: 47.82, currency: "GBP", rating: "Four", in_stock: true, product_url: "https://books.toscrape.com/catalogue/sharp-objects_997/index.html" },
          ],
        },
      },
      {
        id: "ep_books_detail",
        name: "Get Product by ID",
        method: "GET",
        path: "/api/v1/endpoints/books/products/{id}",
        description: "Returns full product specification, description, UPC, and review summary.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://books.toscrape.com",
        parameters: [
          { name: "id", in: "path", type: "string", required: true, defaultValue: "a-light-in-the-attic_1000", description: "Product identifier slug" },
        ],
        responseSchema: {
          type: "object",
          properties: {
            id: { type: "string" },
            title: { type: "string" },
            upc: { type: "string" },
            price_excl_tax: { type: "number" },
            price_incl_tax: { type: "number" },
            tax: { type: "number" },
            availability_count: { type: "integer" },
            description: { type: "string" },
          },
        },
        sampleResponse: {
          id: "a-light-in-the-attic_1000",
          title: "A Light in the Attic",
          upc: "a897fe39b1053632",
          price_excl_tax: 51.77,
          price_incl_tax: 51.77,
          tax: 0.0,
          availability_count: 22,
          description: "It's hard to imagine a world without A Light in the Attic. This now-classic collection of poetry and drawings from Shel Silverstein celebrates its 20th anniversary.",
        },
      },
      {
        id: "ep_books_categories",
        name: "List Book Categories",
        method: "GET",
        path: "/api/v1/endpoints/books/categories",
        description: "Retrieves list of navigation categories with nested URLs and item counts.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://books.toscrape.com",
        parameters: [],
        responseSchema: {
          type: "object",
          properties: {
            categories: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  name: { type: "string" },
                  slug: { type: "string" },
                  count: { type: "integer" },
                },
              },
            },
          },
        },
        sampleResponse: {
          categories: [
            { name: "Travel", slug: "travel_2", count: 11 },
            { name: "Mystery", slug: "mystery_3", count: 32 },
            { name: "Historical Fiction", slug: "historical-fiction_4", count: 26 },
            { name: "Sequential Art", slug: "sequential-art_5", count: 75 },
            { name: "Classics", slug: "classics_6", count: 19 },
          ],
        },
      },
      {
        id: "ep_books_search",
        name: "Search Catalog Query",
        method: "POST",
        path: "/api/v1/endpoints/books/search",
        description: "Executes parametric search and price-range filtering across indexed products.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://books.toscrape.com",
        parameters: [],
        requestBodySchema: {
          type: "object",
          properties: {
            query: { type: "string", description: "Search query text" },
            min_price: { type: "number", description: "Minimum price threshold" },
            max_price: { type: "number", description: "Maximum price threshold" },
            sort_by: { type: "string", enum: ["price_asc", "price_desc", "rating"] },
          },
          required: ["query"],
        },
        responseSchema: {
          type: "object",
          properties: {
            matches_count: { type: "integer" },
            results: { type: "array" },
          },
        },
        sampleResponse: {
          matches_count: 2,
          results: [
            { id: "book_1000", title: "A Light in the Attic", price: 51.77, rating: "Three" },
            { id: "book_997", title: "Sharp Objects", price: 47.82, rating: "Four" },
          ],
        },
      },
    ],
  },

  articles_news: {
    id: "articles_news",
    name: "News & Discussions Portal",
    category: "News",
    url: "https://news.ycombinator.com",
    prompt: "Extract top stories with title, ranking, point score, author username, comments count, and destination link.",
    pageMetadata: {
      url: "https://news.ycombinator.com",
      hostname: "news.ycombinator.com",
      title: "Hacker News",
      httpStatus: 200,
      contentType: "text/html; charset=utf-8",
      elementsInspected: 90,
      captureTime: "2026-10-25 02:19:00 UTC",
      detectedFramework: "Static Table Layout",
    },
    discoveredFields: [
      { name: "rank", type: "number", required: true, description: "Story placement index", sampleValue: 1, selector: "span.rank" },
      { name: "title", type: "string", required: true, description: "Article title headline", sampleValue: "Show HN: MorphAPI Gateway", selector: "span.titleline > a" },
      { name: "url", type: "url", required: true, description: "External source destination link", sampleValue: "https://github.com/Jayant-1/MorphAPI", selector: "span.titleline > a[href]" },
      { name: "points", type: "number", required: true, description: "Community upvotes", sampleValue: 248, selector: "span.score" },
      { name: "by", type: "string", required: true, description: "Submitter username", sampleValue: "jayant", selector: "a.hnuser" },
      { name: "comments_count", type: "number", required: false, description: "Total discussion replies", sampleValue: 84, selector: "a:contains('comments')" },
    ],
    steps: [
      { id: "s1", title: "Request accepted", description: "Target parsed and verified", status: "success", durationMs: 38 },
      { id: "s2", title: "DOM Extraction", description: "Captured 30 item table rows", status: "success", durationMs: 290 },
      { id: "s3", title: "Field Synthesis", description: "Mapped rank, title, points, author, comments", status: "success", durationMs: 210 },
      { id: "s4", title: "Selector Verification", description: "Playwright verified selectors on 30 items", status: "success", durationMs: 160 },
      { id: "s5", title: "Endpoints Ready", description: "Synthesized 3 REST routes", status: "success", durationMs: 75 },
    ],
    logs: [
      { id: "l1", timestamp: "02:19:00.010", severity: "info", source: "Playwright", message: "Fetched HTML from news.ycombinator.com (HTTP 200)" },
      { id: "l2", timestamp: "02:19:00.300", severity: "info", source: "DOMValidator", message: "Parsed 30 rows from table.itemlist" },
      { id: "l3", timestamp: "02:19:00.510", severity: "info", source: "SchemaSynthesis", message: "Generated Pydantic model 'HackerNewsStory'" },
      { id: "l4", timestamp: "02:19:00.745", severity: "info", source: "EndpointGateway", message: "Live endpoints ready for ingestion" },
    ],
    endpoints: [
      {
        id: "ep_hn_top",
        name: "Get Top Stories",
        method: "GET",
        path: "/api/v1/endpoints/news/top",
        description: "Returns currently trending stories sorted by rank.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://news.ycombinator.com",
        parameters: [
          { name: "limit", in: "query", type: "integer", required: false, defaultValue: "30", description: "Number of stories to return" },
        ],
        responseSchema: {
          type: "object",
          properties: {
            stories: { type: "array" },
          },
        },
        sampleResponse: {
          stories: [
            { rank: 1, title: "Show HN: MorphAPI Gateway", points: 248, by: "jayant", comments_count: 84, url: "https://github.com/Jayant-1/MorphAPI" },
            { rank: 2, title: "Deterministic Browser ASTs with Playwright", points: 195, by: "pg", comments_count: 52, url: "https://playwright.dev" },
            { rank: 3, title: "Model Context Protocol for Local Agents", points: 310, by: "alex", comments_count: 112, url: "https://modelcontextprotocol.io" },
          ],
        },
      },
      {
        id: "ep_hn_story",
        name: "Get Story by ID",
        method: "GET",
        path: "/api/v1/endpoints/news/story/{id}",
        description: "Fetches single story metadata and comment thread tree.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://news.ycombinator.com",
        parameters: [
          { name: "id", in: "path", type: "string", required: true, defaultValue: "39482104", description: "Hacker News item ID" },
        ],
        responseSchema: {
          type: "object",
          properties: {
            id: { type: "string" },
            title: { type: "string" },
            points: { type: "integer" },
            author: { type: "string" },
          },
        },
        sampleResponse: {
          id: "39482104",
          title: "Show HN: MorphAPI Gateway",
          points: 248,
          author: "jayant",
          posted_at: "2 hours ago",
          comments_count: 84,
        },
      },
    ],
  },

  releases_github: {
    id: "releases_github",
    name: "Software Releases Portal",
    category: "Software",
    url: "https://github.com/tiangolo/fastapi/releases",
    prompt: "Extract release version tags, release dates, changelog summaries, and direct asset download URLs.",
    pageMetadata: {
      url: "https://github.com/tiangolo/fastapi/releases",
      hostname: "github.com",
      title: "Releases · tiangolo/fastapi",
      httpStatus: 200,
      contentType: "text/html; charset=utf-8",
      elementsInspected: 84,
      captureTime: "2026-10-25 02:18:45 UTC",
      detectedFramework: "Next.js / React Server Components",
    },
    discoveredFields: [
      { name: "version", type: "string", required: true, sampleValue: "0.115.6", selector: "div.release-header a" },
      { name: "release_date", type: "string", required: true, sampleValue: "2026-10-18T10:00:00Z", selector: "relative-time" },
      { name: "changelog", type: "string", required: false, sampleValue: "Add support for Pydantic v2.10 strict validation", selector: "div.markdown-body" },
    ],
    steps: [
      { id: "s1", title: "Request accepted", description: "Target GitHub repo verified", status: "success", durationMs: 32 },
      { id: "s2", title: "DOM Extraction", description: "Extracted release timeline cards", status: "success", durationMs: 340 },
      { id: "s3", title: "Schema Verification", description: "Validated 10 release tags", status: "success", durationMs: 180 },
      { id: "s4", title: "Endpoints Created", description: "Synthesized 2 REST routes", status: "success", durationMs: 65 },
    ],
    logs: [
      { id: "l1", timestamp: "02:18:45.050", severity: "info", source: "Playwright", message: "Parsed release timeline" },
      { id: "l2", timestamp: "02:18:45.390", severity: "info", source: "SchemaSynthesis", message: "SemVer pattern matched 10 release tags" },
      { id: "l3", timestamp: "02:18:45.570", severity: "info", source: "EndpointGateway", message: "2 endpoints active" },
    ],
    endpoints: [
      {
        id: "ep_releases_list",
        name: "List All Releases",
        method: "GET",
        path: "/api/v1/endpoints/fastapi/releases",
        description: "Returns chronological software releases with change notes.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://github.com/tiangolo/fastapi/releases",
        parameters: [],
        responseSchema: {
          type: "object",
          properties: {
            releases: { type: "array" },
          },
        },
        sampleResponse: {
          releases: [
            { version: "0.115.6", date: "2026-10-18", verified: true, prerelease: false },
            { version: "0.115.5", date: "2026-10-12", verified: true, prerelease: false },
            { version: "0.115.4", date: "2026-10-04", verified: true, prerelease: false },
          ],
        },
      },
      {
        id: "ep_releases_latest",
        name: "Get Latest Release",
        method: "GET",
        path: "/api/v1/endpoints/fastapi/releases/latest",
        description: "Returns the latest production stable release tag and tarball URL.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://github.com/tiangolo/fastapi/releases",
        parameters: [],
        responseSchema: {
          type: "object",
          properties: {
            version: { type: "string" },
            date: { type: "string" },
            download_url: { type: "string" },
          },
        },
        sampleResponse: {
          version: "0.115.6",
          date: "2026-10-18T10:00:00Z",
          download_url: "https://github.com/tiangolo/fastapi/archive/refs/tags/0.115.6.tar.gz",
        },
      },
    ],
  },

  empty_output: {
    id: "empty_output",
    name: "Zero Endpoints (No Match Edge Case)",
    category: "Edge Cases",
    url: "https://example.com/empty-directory",
    prompt: "Extract product pricing, inventory sku, and customer reviews.",
    pageMetadata: {
      url: "https://example.com/empty-directory",
      hostname: "example.com",
      title: "Example Domain - Blank Directory",
      httpStatus: 200,
      contentType: "text/html",
      elementsInspected: 12,
      captureTime: "2026-10-25 02:19:30 UTC",
    },
    discoveredFields: [],
    steps: [
      { id: "e1", title: "Target URL loaded", description: "Loaded example.com DOM tree (12 elements total)", status: "success", durationMs: 140 },
      { id: "e2", title: "Field Discovery Scan", description: "Searched DOM for product pricing, SKU, and reviews", status: "warning", durationMs: 250 },
      { id: "e3", title: "Zero Selectors Matched", description: "The requested fields do not exist on this target page", status: "warning", durationMs: 90 },
    ],
    logs: [
      { id: "l1", timestamp: "02:19:30.140", severity: "info", source: "Playwright", message: "Page loaded with 12 elements" },
      { id: "l2", timestamp: "02:19:30.390", severity: "warning", source: "SchemaSynthesis", message: "Zero matches found for 'pricing' or 'SKU' on domain example.com" },
      { id: "l3", timestamp: "02:19:30.480", severity: "warning", source: "EndpointGateway", message: "No endpoints synthesized. Awaiting revised user prompt." },
    ],
    endpoints: [],
  },

  approval_required: {
    id: "approval_required",
    name: "Operator Approval Gate",
    category: "Security & Governance",
    url: "https://internal-portal.corp.local/users",
    prompt: "Extract employee email addresses and role directory.",
    pageMetadata: {
      url: "https://internal-portal.corp.local/users",
      hostname: "internal-portal.corp.local",
      title: "Staff Directory - Internal",
      httpStatus: 200,
      contentType: "text/html",
      elementsInspected: 52,
      captureTime: "2026-10-25 02:19:45 UTC",
    },
    discoveredFields: [
      { name: "email", type: "string", required: true, sampleValue: "staff@corp.local", selector: "td.email" },
      { name: "role", type: "string", required: true, sampleValue: "Infrastructure Lead", selector: "td.role" },
    ],
    steps: [
      { id: "a1", title: "Target inspected", description: "DOM tree analyzed", status: "success", durationMs: 180 },
      { id: "a2", title: "PII & Access Policy Review", description: "Detected corporate intranet hostname and email field", status: "warning", durationMs: 220 },
      { id: "a3", title: "Awaiting Operator Sign-Off", description: "Human-in-the-loop gate triggered before endpoint registration", status: "running", durationMs: 0 },
    ],
    logs: [
      { id: "l1", timestamp: "02:19:45.180", severity: "info", source: "Playwright", message: "Inspected internal directory page" },
      { id: "l2", timestamp: "02:19:45.400", severity: "warning", source: "LangGraph", message: "Governance Policy Alert: Target URL matches private intranet pattern" },
      { id: "l3", timestamp: "02:19:45.405", severity: "warning", source: "EndpointGateway", message: "Approval required from operator before publishing API endpoints" },
    ],
    approvalMessage: "Governance Policy Check: Target domain 'internal-portal.corp.local' appears to be an internal resource containing contact records. Please confirm you have authorization to publish this extraction endpoint.",
    endpoints: [
      {
        id: "ep_staff_directory",
        name: "List Staff Directory",
        method: "GET",
        path: "/api/v1/endpoints/internal/staff",
        description: "Returns staff directory entries. Pending operator approval.",
        status: "approval_required",
        version: "v1.0.0-draft",
        authRequired: true,
        sourceUrl: "https://internal-portal.corp.local/users",
        parameters: [],
        responseSchema: { type: "object" },
        sampleResponse: { note: "Pending approval to unlock live extraction." },
      },
    ],
  },

  recoverable_error: {
    id: "recoverable_error",
    name: "Recoverable Challenge (Anti-Bot Edge Case)",
    category: "Edge Cases",
    url: "https://shielded-site.example.org",
    prompt: "Extract real-time stock quotes and bid-ask spreads.",
    pageMetadata: {
      url: "https://shielded-site.example.org",
      hostname: "shielded-site.example.org",
      httpStatus: 403,
      contentType: "text/html",
      elementsInspected: 4,
      captureTime: "2026-10-25 02:20:00 UTC",
    },
    discoveredFields: [],
    steps: [
      { id: "r1", title: "Initiating browser session", description: "Opening headless Playwright worker", status: "success", durationMs: 120 },
      { id: "r2", title: "Target Access Challenge", description: "Cloudflare Turnstile challenge intercepted (HTTP 403)", status: "error", durationMs: 310 },
      { id: "r3", title: "Extraction Suspended", description: "Retry with stealth browser profile or provide bypass header", status: "pending" },
    ],
    logs: [
      { id: "l1", timestamp: "02:20:00.120", severity: "info", source: "Playwright", message: "Navigating to shielded-site.example.org" },
      { id: "l2", timestamp: "02:20:00.430", severity: "error", source: "Playwright", message: "HTTP 403 Forbidden: Cloudflare JS challenge detected" },
      { id: "l3", timestamp: "02:20:00.435", severity: "warning", source: "LangGraph", message: "Stealth retry available. Operator can re-run with browser stealth flag." },
    ],
    errorMessage: "The target website returned HTTP 403 with an automated challenge. Click 'Retry with Stealth Profile' to rotate browser fingerprint and re-attempt extraction.",
    endpoints: [],
  },

  test_failure: {
    id: "test_failure",
    name: "Test Failure Simulation",
    category: "Edge Cases",
    url: "https://books.toscrape.com",
    prompt: "Extract product catalog with failing downstream endpoint test.",
    pageMetadata: {
      url: "https://books.toscrape.com",
      hostname: "books.toscrape.com",
      title: "Books to Scrape",
      httpStatus: 200,
      elementsInspected: 50,
      captureTime: "2026-10-25 02:20:10 UTC",
    },
    discoveredFields: [
      { name: "title", type: "string", required: true, sampleValue: "Sample Book", selector: "h3 a" },
    ],
    steps: [
      { id: "t1", title: "Extraction ready", description: "Endpoints generated", status: "success", durationMs: 250 },
    ],
    logs: [
      { id: "l1", timestamp: "02:20:10.050", severity: "info", source: "EndpointGateway", message: "Endpoint active with simulated test error condition" },
    ],
    testFailureEndpointId: "ep_failing_route",
    endpoints: [
      {
        id: "ep_failing_route",
        name: "Legacy Product Lookup (Fails 404)",
        method: "GET",
        path: "/api/v1/endpoints/books/legacy-lookup",
        description: "An endpoint whose downstream target path moved, returning a simulated HTTP 404 in the test workbench.",
        status: "ready",
        version: "v1.0.0",
        authRequired: false,
        sourceUrl: "https://books.toscrape.com",
        parameters: [
          { name: "sku", in: "query", type: "string", required: true, defaultValue: "missing-sku-999", description: "Target product SKU" },
        ],
        responseSchema: { type: "object" },
        sampleResponse: { error: "Resource not found on upstream target" },
      },
    ],
  },
};
