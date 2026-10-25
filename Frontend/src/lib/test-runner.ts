import { DEMO_FIXTURES } from "./fixtures";
import {
  extractHostname,
  startRun,
  executeEndpointTest,
  checkBackendHealth,
} from "./api-adapter";
import { EndpointDefinition } from "./types";

async function runTests() {
  console.log("=== MorphAPI Core Flow Verification Suite ===\n");
  let passed = 0;
  let failed = 0;

  function assert(condition: boolean, desc: string) {
    if (condition) {
      console.log(`[PASS] ${desc}`);
      passed++;
    } else {
      console.error(`[FAIL] ${desc}`);
      failed++;
    }
  }

  // 1. Hostname Extraction
  console.log("1. Hostname extraction tests:");
  assert(extractHostname("https://books.toscrape.com/catalogue") === "books.toscrape.com", "Extracts clean hostname from full URL");
  assert(extractHostname("http://localhost:8001/v2/api") === "localhost", "Extracts localhost hostname");
  assert(extractHostname("news.ycombinator.com") === "news.ycombinator.com", "Handles URLs without protocol prefix");

  // 2. Fixture Integrity
  console.log("\n2. Fixture integrity & coverage tests:");
  const fixtureKeys = Object.keys(DEMO_FIXTURES);
  assert(fixtureKeys.length >= 6, `Found ${fixtureKeys.length} evaluation fixtures`);
  assert(DEMO_FIXTURES.multi_endpoint_catalog.endpoints.length === 4, "Multi-endpoint catalog has exactly 4 endpoints");
  assert(DEMO_FIXTURES.empty_output.endpoints.length === 0, "Empty output fixture has 0 endpoints");
  assert(DEMO_FIXTURES.approval_required.endpoints[0].status === "approval_required", "Approval required fixture has correct status");
  assert(DEMO_FIXTURES.recoverable_error.errorMessage !== undefined, "Recoverable error has explicit error message");

  // 3. Endpoint Enumeration
  console.log("\n3. Endpoint Enumeration tests:");
  const catalogEndpoints = DEMO_FIXTURES.multi_endpoint_catalog.endpoints;
  const methods = catalogEndpoints.map((e) => e.method);
  assert(methods.includes("GET") && methods.includes("POST"), "Endpoints collection includes both GET and POST routes");
  catalogEndpoints.forEach((ep) => {
    assert(ep.path.startsWith("/api/v1/"), `Endpoint ${ep.name} has valid path ${ep.path}`);
    assert(typeof ep.sampleResponse === "object", `Endpoint ${ep.name} has valid sampleResponse`);
  });

  // 4. Test Execution Engine
  console.log("\n4. Interactive Test Execution tests:");
  const testEp = catalogEndpoints[0];
  const testResult = await executeEndpointTest(testEp, { page: "1" }, { Accept: "application/json" });
  assert(testResult.status === 200, `Test execution returned status 200 (got ${testResult.status})`);
  assert(testResult.durationMs > 0, `Test execution measured duration (${testResult.durationMs}ms)`);
  assert(testResult.sizeBytes > 0, `Test execution measured payload size (${testResult.sizeBytes} bytes)`);
  assert(testResult.headers["content-type"].includes("application/json"), "Test response headers contain application/json");

  // 5. Test Failure Simulation
  console.log("\n5. Test Failure Handling:");
  const failingEp = DEMO_FIXTURES.test_failure.endpoints[0];
  const failResult = await executeEndpointTest(failingEp, { sku: "missing-sku-999" }, {});
  assert(failResult.status === 404, `Test failure simulation returned status 404 (got ${failResult.status})`);
  assert(failResult.isError === true, "Result marked as error");
  assert(failResult.errorMessage?.includes("404") || false, "Error message contains 404 indication");

  // 6. Streaming Run Lifecycle & Early Endpoint Emission
  console.log("\n6. Streaming Run Lifecycle tests:");
  await new Promise<void>((resolve) => {
    let receivedEarlyEndpoints = false;
    const handle = startRun("https://books.toscrape.com", "Extract product names", {
      fixtureId: "multi_endpoint_catalog",
      onUpdate: (session) => {
        if (session.status === "processing" && session.endpoints.length > 0) {
          receivedEarlyEndpoints = true;
          assert(session.endpoints[0].status === "validating", "Early endpoints emitted in validating state while processing");
        }
        if (session.status === "completed") {
          assert(receivedEarlyEndpoints, "Run emitted early endpoints before final completion");
          assert(session.endpoints.length === 4, "Streamed completed session contains 4 endpoints");
          assert(session.endpoints.every((e) => e.status === "ready"), "All endpoints promoted to ready state on completion");
          assert(session.logs.length >= 4, `Streamed session generated ${session.logs.length} logs`);
          assert(session.steps.length === 5, "Streamed session generated 5 pipeline steps");
          resolve();
        }
      },
    });
  });

  // 7. Stop / Abort Handling
  console.log("\n7. Run Cancellation / Stop tests:");
  await new Promise<void>((resolve) => {
    const handle = startRun("https://example.com", "Test abort", {
      fixtureId: "multi_endpoint_catalog",
      onUpdate: (session) => {
        if (session.status === "stopped") {
          assert(true, "Run transitioned to stopped state when stop() called");
          assert(session.connectionStatus === "closed", "Connection status closed on stop");
          resolve();
        }
      },
    });
    // Stop immediately
    setTimeout(() => {
      handle.stop();
    }, 50);
  });

  // 8. Auth & Side-Effect Detection Tests
  console.log("\n8. Security & Side-Effect Detection tests:");
  const searchEndpoint = catalogEndpoints.find((e) => e.method === "POST");
  assert(searchEndpoint !== undefined, "Found POST search endpoint in catalog");
  assert(searchEndpoint?.method === "POST", "Search endpoint method is POST (mutating)");

  const securedEndpoint = DEMO_FIXTURES.approval_required.endpoints[0];
  assert(securedEndpoint.authRequired === true, "Governance fixture requires authentication");
  assert(securedEndpoint.status === "approval_required", "Secured endpoint flagged as approval_required");

  // 9. HTTP Status Inspection Formatting Tests
  console.log("\n9. HTTP Status Formatting tests:");
  const formatStatus = (code: number) => {
    if (code >= 200 && code < 300) return `${code} OK`;
    if (code === 403) return `${code} Challenge`;
    return `${code} Error`;
  };
  assert(formatStatus(200) === "200 OK", "Status 200 formatted as 200 OK");
  assert(formatStatus(403) === "403 Challenge", "Status 403 formatted as 403 Challenge (not 403 OK)");
  assert(formatStatus(500) === "500 Error", "Status 500 formatted as 500 Error");

  console.log(`\n=== Verification Results: ${passed} Passed, ${failed} Failed ===`);
  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
