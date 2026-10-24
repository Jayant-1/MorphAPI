export type RunStatus =
  | "idle"
  | "submitting"
  | "connecting"
  | "processing"
  | "awaiting_approval"
  | "completed"
  | "failed"
  | "stopped";

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "streaming"
  | "reconnecting"
  | "closed";

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface FieldDefinition {
  name: string;
  type: "string" | "number" | "boolean" | "array" | "object" | "url";
  description?: string;
  required: boolean;
  sampleValue?: string | number | boolean;
  selector?: string;
  confidence?: number;
}

export interface V2ParameterSpec {
  name: string;
  type: "str" | "int" | "float" | "bool" | string;
  location: "query" | "path" | "body" | string;
  default?: unknown;
  required: boolean;
  description?: string;
  enum_values?: string[] | null;
}

export interface V2FieldTypeSpec {
  name: string;
  target_type: string;
  clean_regex?: string | null;
  default?: unknown;
  description?: string;
}

export interface V2EndpointContract {
  response_shape: "list" | "single_object" | "paginated" | string;
  parameters: V2ParameterSpec[];
  fields: V2FieldTypeSpec[];
  http_methods: string[];
}

export interface EndpointV2Response {
  endpoint_id: string;
  user_id: string;
  api_name: string;
  slug: string;
  name: string;
  status: string;
  target_url: string;
  api_key: string;
  endpoint_url: string;
  full_endpoint_url: string;
  openapi_url?: string | null;
  docs_url?: string | null;
  curl_command: string;
  api_specification?: Record<string, unknown>;
  contract?: V2EndpointContract | null;
  schema_definition: Record<string, string>;
  sample_data: Record<string, unknown>[];
  message: string;
}

export interface EndpointParameter {
  name: string;
  in: "query" | "path" | "header" | "body";
  type: string;
  required: boolean;
  defaultValue?: string | number | boolean;
  description?: string;
}

export interface EndpointDefinition {
  id: string;
  name: string;
  method: HttpMethod;
  supportedMethods?: HttpMethod[];
  path: string;
  fullUrl?: string;
  openapiUrl?: string;
  docsUrl?: string;
  description: string;
  status: "ready" | "draft" | "validating" | "approval_required" | "failed";
  version: string;
  authRequired: boolean;
  authType?: string;
  apiKey?: string;
  sourceUrl: string;
  parameters: EndpointParameter[];
  contract?: V2EndpointContract | null;
  v2Response?: EndpointV2Response;
  requestBodySchema?: Record<string, unknown>;
  responseSchema: Record<string, unknown>;
  sampleResponse: Record<string, unknown> | unknown[];
  cUrlTemplate?: string;
  jsSnippet?: string;
  pySnippet?: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  severity: "info" | "warning" | "error" | "debug";
  source: "Playwright" | "DOMValidator" | "SchemaSynthesis" | "EndpointGateway" | "LangGraph";
  message: string;
}

export interface PipelineStep {
  id: string;
  title: string;
  description: string;
  status: "pending" | "running" | "success" | "warning" | "error";
  durationMs?: number;
  details?: string;
}

export interface PageMetadata {
  url: string;
  hostname: string;
  title?: string;
  httpStatus?: number;
  contentType?: string;
  elementsInspected?: number;
  captureTime?: string;
  screenshotUrl?: string;
  detectedFramework?: string;
}

export interface TestExecutionResult {
  endpointId: string;
  status: number;
  statusText: string;
  durationMs: number;
  sizeBytes: number;
  headers: Record<string, string>;
  data: unknown;
  rawText?: string;
  executedAt: string;
  method?: HttpMethod;
  requestUrl?: string;
  requestParams?: Record<string, unknown>;
  isError?: boolean;
  errorMessage?: string;
  isDemoSample?: boolean;
}

export interface RunSession {
  id: string;
  targetUrl: string;
  prompt: string;
  createdAt: string;
  status: RunStatus;
  connectionStatus: ConnectionStatus;
  pageMetadata?: PageMetadata;
  steps: PipelineStep[];
  discoveredFields: FieldDefinition[];
  endpoints: EndpointDefinition[];
  logs: LogEntry[];
  approvalMessage?: string;
  errorMessage?: string;
  canRetry?: boolean;
  isDemo?: boolean;
  v2Response?: EndpointV2Response;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  targetUrl?: string;
  createdAt: string;
  runSession?: RunSession;
  status?: "streaming" | "completed" | "error" | "awaiting_approval";
  endpoints?: EndpointDefinition[];
  v2Response?: EndpointV2Response;
  selectedTestEndpointId?: string;
  isActivityExpanded?: boolean;
}

export type AGUIEventType =
  | "lifecycle:start"
  | "lifecycle:step_update"
  | "lifecycle:field_discovered"
  | "lifecycle:endpoints_ready"
  | "lifecycle:approval_required"
  | "lifecycle:complete"
  | "lifecycle:error"
  | "log:entry"
  | "preview:metadata";

export interface AGUIEvent {
  type: AGUIEventType;
  runId: string;
  timestamp: string;
  payload: unknown;
}
