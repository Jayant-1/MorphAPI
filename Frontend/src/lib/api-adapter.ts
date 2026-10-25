import {
  RunSession,
  TestExecutionResult,
  EndpointDefinition,
  LogEntry,
  PipelineStep,
  EndpointV2Response,
  HttpMethod,
} from "./types";
import { DEMO_FIXTURES, DemoFixture } from "./fixtures";

export interface RunOptions {
  fixtureId?: string;
  forceDemo?: boolean;
  onUpdate: (session: RunSession) => void;
  onComplete?: (session: RunSession) => void;
  onError?: (error: string) => void;
}

export interface ActiveRunHandle {
  runId: string;
  stop: () => void;
}

// Configurable V2 Base URL (default: http://localhost:8001)
export function getV2BaseUrl(): string {
  if (typeof window !== "undefined") {
    return (
      (window as any).__MORPHAPI_V2_URL ||
      process.env.NEXT_PUBLIC_MORPHAPI_V2_URL ||
      "http://localhost:8001"
    );
  }
  return process.env.NEXT_PUBLIC_MORPHAPI_V2_URL || "http://localhost:8001";
}

// Generate short stable identifier
export function generateRunId(): string {
  return "run_" + Math.random().toString(36).substring(2, 9);
}

// Extract human-readable hostname
export function extractHostname(rawUrl: string): string {
  try {
    const parsed = new URL(rawUrl.startsWith("http") ? rawUrl : `https://${rawUrl}`);
    return parsed.hostname;
  } catch {
    return rawUrl.replace(/^https?:\/\//, "").split("/")[0] || "website.target";
  }
}

// Check live V2 backend health
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1800);
    const baseUrl = getV2BaseUrl();
    const res = await fetch(`${baseUrl}/v2/health`, {
      signal: controller.signal,
      method: "GET",
    });
    clearTimeout(timeout);
    return res.ok;
  } catch {
    return false;
  }
}

// Detailed health query returning version and connection details
export async function checkV2HealthDetails(): Promise<{
  connected: boolean;
  url: string;
  version?: string;
}> {
  const url = getV2BaseUrl();
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    const res = await fetch(`${url}/v2/health`, {
      signal: controller.signal,
      method: "GET",
    });
    clearTimeout(timeout);
    if (res.ok) {
      const data = await res.json();
      return { connected: true, url, version: data.version || "2.0.0" };
    }
    return { connected: false, url };
  } catch {
    return { connected: false, url };
  }
}

/**
 * Normalizes single EndpointV2Response from morphapi_v2 into view model EndpointDefinition.
 * Does NOT invent multiple endpoints from a single V2 response.
 */
export function normalizeV2Endpoint(
  v2: EndpointV2Response,
  sourceUrl?: string
): EndpointDefinition {
  const baseUrl = getV2BaseUrl();
  const fullUrl = v2.full_endpoint_url || `${baseUrl}${v2.endpoint_url}`;
  const openapiUrl = v2.openapi_url || `${baseUrl}${v2.endpoint_url}/openapi.json`;
  const docsUrl = v2.docs_url || `${baseUrl}${v2.endpoint_url}/docs`;
  const supportedMethods =
    (v2.contract?.http_methods as HttpMethod[]) || ["GET", "POST"];

  const parameters = (v2.contract?.parameters || []).map((p) => ({
    name: p.name,
    in: (p.location as any) || "query",
    type: p.type || "string",
    required: !!p.required,
    defaultValue: p.default != null ? String(p.default) : "",
    description: p.description || "",
  }));

  // If contract has no parameters, check if inputs dict exists
  if (parameters.length === 0 && (v2 as any).inputs) {
    Object.entries((v2 as any).inputs).forEach(([k, v]) => {
      parameters.push({
        name: k,
        in: "query",
        type: typeof v === "object" ? "object" : "string",
        required: false,
        defaultValue: typeof v === "string" ? v : "",
        description: `Input parameter for ${k}`,
      });
    });
  }

  return {
    id: v2.endpoint_id || `ep_v2_${v2.slug}`,
    name: v2.api_name || v2.slug || "Synthesized API",
    method: supportedMethods[0] || "GET",
    supportedMethods,
    path: v2.endpoint_url,
    fullUrl,
    openapiUrl,
    docsUrl,
    description:
      v2.message ||
      (v2.contract?.response_shape
        ? `Synthesized ${v2.contract.response_shape} endpoint for ${v2.target_url}`
        : `Verified extraction endpoint for ${v2.target_url}`),
    status: "ready",
    version: "2.0.0",
    authRequired: false,
    apiKey: v2.api_key,
    sourceUrl: v2.target_url || sourceUrl || "",
    parameters,
    contract: v2.contract,
    v2Response: v2,
    responseSchema: v2.schema_definition,
    sampleResponse: v2.sample_data,
    cUrlTemplate: v2.curl_command || `curl '${fullUrl}'`,
  };
}

/**
 * Standard LangGraph pipeline steps corresponding to morphapi_v2 workflows/graph.py
 */
function createDefaultV2Steps(hostname: string): PipelineStep[] {
  return [
    {
      id: "parse_intent",
      title: "Parse Intent & Scope",
      description: `Analyzing target URL and extracting requested fields for ${hostname}`,
      status: "running",
    },
    {
      id: "inspect_and_sniff",
      title: "Inspect DOM & Sniff Network APIs",
      description: "Launching Playwright headless session to observe DOM and API calls",
      status: "pending",
    },
    {
      id: "propose_plan",
      title: "Propose Extraction Plan",
      description: "Synthesizing DOM cluster hierarchy or custom browser extraction logic",
      status: "pending",
    },
    {
      id: "test_extraction",
      title: "Test Live Extraction",
      description: "Executing candidate plan against target page and extracting records",
      status: "pending",
    },
    {
      id: "validate_results",
      title: "Validate Schema & Coverage",
      description: "Verifying record completeness, type coercion, and non-empty guarantees",
      status: "pending",
    },
    {
      id: "activate_endpoint",
      title: "Activate Production Endpoint",
      description: "Registering dynamic route in gateway and generating OpenAPI 3.1 specification",
      status: "pending",
    },
  ];
}

/**
 * Starts an agent run session.
 * The DEFAULT and PRIMARY path is the real morphapi_v2 backend on port 8001.
 * If forceDemo is explicitly true, runs the requested deterministic demo fixture.
 */
export function startRun(
  targetUrl: string,
  prompt: string,
  options: RunOptions
): ActiveRunHandle {
  const runId = generateRunId();
  let isCancelled = false;
  const timeoutIds: NodeJS.Timeout[] = [];

  const cleanup = () => {
    isCancelled = true;
    timeoutIds.forEach(clearTimeout);
    timeoutIds.length = 0;
  };

  const scheduleTimeout = (fn: () => void, delayMs: number) => {
    if (isCancelled) return;
    const id = setTimeout(() => {
      if (!isCancelled) fn();
    }, delayMs);
    timeoutIds.push(id);
  };

  const hostname = extractHostname(targetUrl);

  // ─────────────────────────────────────────────────────────────────────────────
  // OPT-IN DEMO MODE: Only if forceDemo is explicitly requested
  // ─────────────────────────────────────────────────────────────────────────────
  if (options.forceDemo) {
    let fixture: DemoFixture | null = null;
    if (options.fixtureId && DEMO_FIXTURES[options.fixtureId]) {
      fixture = DEMO_FIXTURES[options.fixtureId];
    } else {
      fixture = DEMO_FIXTURES.multi_endpoint_catalog;
    }

    const demoSession: RunSession = {
      id: runId,
      targetUrl,
      prompt,
      createdAt: new Date().toISOString(),
      status: "connecting",
      connectionStatus: "connecting",
      isDemo: true,
      pageMetadata: fixture.pageMetadata,
      steps: [
        {
          id: "step_demo_init",
          title: "Starting Demo Simulation",
          description: `Loading scenario: ${fixture.name}`,
          status: "running",
        },
      ],
      discoveredFields: [],
      endpoints: [],
      logs: [
        {
          id: "log_demo_0",
          timestamp: new Date().toLocaleTimeString(),
          severity: "info",
          source: "LangGraph",
          message: `[Demo Sandbox] Running pre-recorded scenario for ${fixture.url}`,
        },
      ],
    };

    options.onUpdate({ ...demoSession });

    scheduleTimeout(() => {
      if (isCancelled) return;
      const runningSession: RunSession = {
        ...demoSession,
        status: "processing",
        connectionStatus: "streaming",
        steps: fixture.steps.map((s, idx) => ({
          ...s,
          status: idx === 0 ? "success" : idx === 1 ? "running" : "pending",
        })),
        discoveredFields: fixture.discoveredFields.slice(0, 3),
        logs: fixture.logs.slice(0, 2),
      };
      options.onUpdate(runningSession);
    }, 600);

    scheduleTimeout(() => {
      if (isCancelled) return;
      const completedSession: RunSession = {
        ...demoSession,
        status: "completed",
        connectionStatus: "closed",
        steps: fixture.steps.map((s) => ({ ...s, status: "success" })),
        discoveredFields: fixture.discoveredFields,
        endpoints: fixture.endpoints,
        logs: fixture.logs,
      };
      options.onUpdate(completedSession);
      options.onComplete?.(completedSession);
    }, 1800);

    return { runId, stop: cleanup };
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // DEFAULT REAL PATH: morphapi_v2 Backend on Port 8001
  // ─────────────────────────────────────────────────────────────────────────────
  const initialSteps = createDefaultV2Steps(hostname);
  const initialSession: RunSession = {
    id: runId,
    targetUrl,
    prompt,
    createdAt: new Date().toISOString(),
    status: "processing",
    connectionStatus: "connecting",
    isDemo: false,
    pageMetadata: {
      url: targetUrl,
      hostname,
      title: `${hostname} - Processing`,
      captureTime: new Date().toISOString(),
    },
    steps: initialSteps,
    discoveredFields: [],
    endpoints: [],
    logs: [
      {
        id: "log_init",
        timestamp: new Date().toLocaleTimeString(),
        severity: "info",
        source: "LangGraph",
        message: `Connecting to MorphAPI V2 Gateway at ${getV2BaseUrl()}`,
      },
      {
        id: "log_dispatch",
        timestamp: new Date().toLocaleTimeString(),
        severity: "info",
        source: "Playwright",
        message: `Synthesizing endpoint for target: ${targetUrl}`,
      },
    ],
  };

  options.onUpdate({ ...initialSession });

  // Progressive step updates while backend executes
  let currentStepIndex = 0;
  const progressInterval = setInterval(() => {
    if (isCancelled) {
      clearInterval(progressInterval);
      return;
    }
    if (currentStepIndex < 4) {
      currentStepIndex++;
      initialSession.steps = initialSession.steps.map((step, idx) => {
        if (idx < currentStepIndex) return { ...step, status: "success", durationMs: 400 + idx * 250 };
        if (idx === currentStepIndex) return { ...step, status: "running" };
        return { ...step, status: "pending" };
      });
      options.onUpdate({ ...initialSession });
    }
  }, 1200);

  // Execute real backend POST /v2/endpoints/synthesize
  const baseUrl = getV2BaseUrl();
  const startTime = performance.now();

  fetch(`${baseUrl}/v2/endpoints/synthesize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      target_url: targetUrl,
      prompt: prompt || `Extract structured data from ${targetUrl}`,
      user_id: "default",
    }),
  })
    .then(async (res) => {
      clearInterval(progressInterval);
      if (isCancelled) return;

      const durationMs = Math.round(performance.now() - startTime);

      if (!res.ok) {
        let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
        try {
          const errData = await res.json();
          if (errData && errData.detail) {
            errorDetail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
          }
        } catch {
          // keep generic errorDetail
        }

        const failedSession: RunSession = {
          ...initialSession,
          status: "failed",
          connectionStatus: "closed",
          canRetry: true,
          errorMessage: errorDetail,
          steps: initialSession.steps.map((step, idx) => {
            if (idx === currentStepIndex) return { ...step, status: "error" };
            if (idx < currentStepIndex) return { ...step, status: "success" };
            return { ...step, status: "pending" };
          }),
          logs: [
            ...initialSession.logs,
            {
              id: "log_err_" + Date.now(),
              timestamp: new Date().toLocaleTimeString(),
              severity: "error",
              source: "EndpointGateway",
              message: `Synthesis failed (${durationMs}ms): ${errorDetail}`,
            },
          ],
        };

        options.onUpdate(failedSession);
        options.onError?.(errorDetail);
        return;
      }

      const v2Response: EndpointV2Response = await res.json();
      const endpoint = normalizeV2Endpoint(v2Response, targetUrl);

      // Extract discovered fields for UI display
      const discoveredFields = Object.entries(v2Response.schema_definition || {}).map(
        ([name, type]) => ({
          name,
          type: (type as any) || "string",
          required: true,
          confidence: 0.98,
        })
      );

      const completedSession: RunSession = {
        ...initialSession,
        status: "completed",
        connectionStatus: "closed",
        canRetry: false,
        steps: initialSession.steps.map((step, idx) => ({
          ...step,
          status: "success",
          durationMs: idx === initialSession.steps.length - 1 ? durationMs : 300 + idx * 150,
        })),
        discoveredFields,
        endpoints: [endpoint],
        v2Response,
        logs: [
          ...initialSession.logs,
          {
            id: "log_done_1",
            timestamp: new Date().toLocaleTimeString(),
            severity: "info",
            source: "EndpointGateway",
            message: `Endpoint synthesized in ${durationMs}ms: ${endpoint.path}`,
          },
          {
            id: "log_done_2",
            timestamp: new Date().toLocaleTimeString(),
            severity: "info",
            source: "SchemaSynthesis",
            message: `Generated OpenAPI 3.1 schema and interactive Swagger UI`,
          },
        ],
      };

      options.onUpdate(completedSession);
      options.onComplete?.(completedSession);
    })
    .catch((err: Error) => {
      clearInterval(progressInterval);
      if (isCancelled) return;

      const durationMs = Math.round(performance.now() - startTime);
      const isConnectionRefused =
        err.message.includes("Failed to fetch") ||
        err.message.includes("NetworkError") ||
        err.message.includes("ECONNREFUSED");

      const errorMessage = isConnectionRefused
        ? `Could not reach MorphAPI V2 Gateway at ${baseUrl}. Please ensure the backend server is running on port 8001 (uvicorn morphapi_v2.api.app:app --port 8001).`
        : `Network error: ${err.message}`;

      const failedSession: RunSession = {
        ...initialSession,
        status: "failed",
        connectionStatus: "closed",
        canRetry: true,
        errorMessage,
        steps: initialSession.steps.map((step, idx) => {
          if (idx === currentStepIndex) return { ...step, status: "error" };
          return step;
        }),
        logs: [
          ...initialSession.logs,
          {
            id: "log_err_" + Date.now(),
            timestamp: new Date().toLocaleTimeString(),
            severity: "error",
            source: "LangGraph",
            message: `Connection error (${durationMs}ms): ${errorMessage}`,
          },
        ],
      };

      options.onUpdate(failedSession);
      options.onError?.(errorMessage);
    });

  return {
    runId,
    stop: () => {
      cleanup();
      clearInterval(progressInterval);
      const stoppedSession: RunSession = {
        ...initialSession,
        status: "stopped",
        connectionStatus: "closed",
        logs: [
          ...initialSession.logs,
          {
            id: "log_stop",
            timestamp: new Date().toLocaleTimeString(),
            severity: "warning",
            source: "LangGraph",
            message: "Synthesis cancelled by user.",
          },
        ],
      };
      options.onUpdate(stoppedSession);
    },
  };
}

/**
 * Executes a live test against an endpoint.
 * Directly queries the live morphapi_v2 gateway at http://localhost:8001/v2/api/{user_id}/{slug}
 * with genuine HTTP status, latency, headers, and returned data.
 */
export async function executeEndpointTest(
  endpoint: EndpointDefinition,
  paramValues: Record<string, string>,
  headers: Record<string, string>,
  body?: string,
  method?: HttpMethod
): Promise<TestExecutionResult> {
  const selectedMethod: HttpMethod = method || endpoint.method || "GET";
  const startTime = performance.now();
  const baseUrl = getV2BaseUrl();

  // If this is an explicit demo endpoint without a real V2 backend URL
  if (endpoint.sampleResponse && !endpoint.fullUrl && endpoint.id !== "ep_failing_route") {
    await new Promise((r) => setTimeout(r, 90));
    const duration = Math.round(performance.now() - startTime);
    return {
      endpointId: endpoint.id,
      status: 200,
      statusText: "OK",
      durationMs: duration,
      sizeBytes: JSON.stringify(endpoint.sampleResponse).length,
      headers: { "content-type": "application/json" },
      data: endpoint.sampleResponse,
      rawText: JSON.stringify(endpoint.sampleResponse, null, 2),
      executedAt: new Date().toISOString(),
      method: selectedMethod,
      isDemoSample: true,
    };
  }

  // Simulated failure endpoint
  if (endpoint.id === "ep_failing_route") {
    await new Promise((r) => setTimeout(r, 60));
    const duration = Math.round(performance.now() - startTime);
    return {
      endpointId: endpoint.id,
      status: 404,
      statusText: "Not Found",
      durationMs: duration,
      sizeBytes: 42,
      headers: { "content-type": "application/json" },
      data: { error: "404 Not Found", detail: "Target resource sku 'missing-sku-999' was not found in catalog." },
      rawText: JSON.stringify({ error: "404 Not Found", detail: "Target resource sku 'missing-sku-999' was not found in catalog." }, null, 2),
      executedAt: new Date().toISOString(),
      method: selectedMethod,
      isError: true,
      errorMessage: "HTTP 404 Not Found: Target resource sku 'missing-sku-999' was not found in catalog.",
    };
  }

  // Construct target URL for live V2 query endpoint
  let targetUrlStr = endpoint.fullUrl || `${baseUrl}${endpoint.path}`;
  try {
    const urlObj = new URL(targetUrlStr, baseUrl);

    // Apply query parameters for GET
    if (selectedMethod === "GET") {
      Object.entries(paramValues).forEach(([k, v]) => {
        if (v && v.trim() !== "") {
          urlObj.searchParams.set(k, v.trim());
        }
      });
    }

    targetUrlStr = urlObj.toString();
  } catch {
    // If URL parsing fails, retain targetUrlStr
  }

  // Build request options
  const reqHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };

  if (endpoint.apiKey) {
    reqHeaders["X-API-Key"] = endpoint.apiKey;
  }

  let reqBody: string | undefined = undefined;
  if (selectedMethod === "POST") {
    reqHeaders["Content-Type"] = "application/json";
    if (body && body.trim() !== "") {
      reqBody = body;
    } else {
      // Build body from paramValues
      reqBody = JSON.stringify(paramValues);
    }
  }

  try {
    const res = await fetch(targetUrlStr, {
      method: selectedMethod,
      headers: reqHeaders,
      body: reqBody,
    });

    const duration = Math.round(performance.now() - startTime);
    const contentType = res.headers.get("content-type") || "";
    let data: unknown;
    let rawText: string;

    if (contentType.includes("application/json")) {
      data = await res.json();
      rawText = JSON.stringify(data, null, 2);
    } else {
      rawText = await res.text();
      try {
        data = JSON.parse(rawText);
      } catch {
        data = rawText;
      }
    }

    const responseHeaders: Record<string, string> = {};
    res.headers.forEach((val, key) => {
      responseHeaders[key] = val;
    });

    return {
      endpointId: endpoint.id,
      status: res.status,
      statusText: res.statusText || (res.ok ? "OK" : "Error"),
      durationMs: duration,
      sizeBytes: new TextEncoder().encode(rawText).length,
      headers: responseHeaders,
      data,
      rawText,
      executedAt: new Date().toISOString(),
      method: selectedMethod,
      requestUrl: targetUrlStr,
      requestParams: paramValues,
      isError: !res.ok,
      errorMessage: !res.ok
        ? typeof (data as any)?.detail === "string"
          ? (data as any).detail
          : `HTTP ${res.status}: ${res.statusText}`
        : undefined,
      isDemoSample: false,
    };
  } catch (err: any) {
    const duration = Math.round(performance.now() - startTime);
    return {
      endpointId: endpoint.id,
      status: 0,
      statusText: "Connection Failed",
      durationMs: duration,
      sizeBytes: 0,
      headers: {},
      data: { error: err.message || "Failed to execute request against gateway" },
      rawText: JSON.stringify({ error: err.message }, null, 2),
      executedAt: new Date().toISOString(),
      method: selectedMethod,
      requestUrl: targetUrlStr,
      requestParams: paramValues,
      isError: true,
      errorMessage: `Failed to connect to ${targetUrlStr}: ${err.message}`,
      isDemoSample: false,
    };
  }
}

/**
 * Handles conversation follow-up refinements by calling the real morphapi_v2 backend.
 */
export function startFollowUpRun(
  previousSession: RunSession,
  followUpPrompt: string,
  options: RunOptions
): ActiveRunHandle {
  const targetUrl = previousSession.targetUrl;
  const combinedPrompt = `${previousSession.prompt}. Refinement: ${followUpPrompt}`;

  return startRun(targetUrl, combinedPrompt, options);
}

/**
 * Lists all stored endpoints saved in morphapi_v2 database
 */
export async function listStoredEndpoints(userId?: string): Promise<any[]> {
  const baseUrl = getV2BaseUrl();
  try {
    const url = userId
      ? `${baseUrl}/v2/endpoints?user_id=${encodeURIComponent(userId)}`
      : `${baseUrl}/v2/endpoints`;
    const res = await fetch(url, { method: "GET" });
    if (res.ok) {
      return await res.json();
    }
    return [];
  } catch {
    return [];
  }
}
