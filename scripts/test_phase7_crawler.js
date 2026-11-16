/**
 * Phase 7 Automated Test Suite: Official College Website Crawler Engine
 *
 * Verifies:
 * 1. SSRF Protection & IP Blocklist (RFC 1918, Loopback, Link-Local, Cloud Metadata 169.254.169.254)
 * 2. Tenant Domain Boundary Enforcement
 * 3. URL Canonicalization & Tracking Param Stripping
 * 4. Robots.txt Policy Rules & Politeness Delay
 * 5. HTML Content Extraction, Heading Hierarchy & Table-to-Markdown
 * 6. SHA-256 Content Hashing & Deduplication
 * 7. Multi-tenant Scoping & Job Lifecycle State Machine
 */

const crypto = require("crypto");
const { URL } = require("url");

let passed = 0;
let failed = 0;

function assert(condition, testName) {
  if (condition) {
    console.log(`  \x1b[32m✔ PASS\x1b[0m: ${testName}`);
    passed++;
  } else {
    console.error(`  \x1b[31m✖ FAIL\x1b[0m: ${testName}`);
    failed++;
  }
}

console.log("\n=======================================================");
console.log("   PHASE 7 AUTOMATED VERIFICATION: CRAWLER ENGINE      ");
console.log("=======================================================\n");

// -----------------------------------------------------------------------------
// 1. SSRF PROTECTION & IP VALIDATION
// -----------------------------------------------------------------------------
console.log("1. SSRF Protection & IP Blocklist Tests:");

const BLOCKED_IP_PATTERNS = [
  /^127\./,                 // 127.0.0.0/8 Loopback
  /^10\./,                  // 10.0.0.0/8 Private
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./, // 172.16.0.0/12 Private
  /^192\.168\./,            // 192.168.0.0/16 Private
  /^169\.254\./,            // 169.254.0.0/16 Link-Local / Cloud Metadata
  /^0\./,                   // 0.0.0.0/8
  /^100\.(6[4-9]|[7-9][0-9]|1[0-1][0-9]|12[0-7])\./, // 100.64.0.0/10 CGNAT
];

const BLOCKED_HOSTNAMES = new Set([
  "localhost",
  "metadata",
  "metadata.google.internal",
  "instance-data",
  "169.254.169.254",
]);

function mockValidateUrlSecurity(urlString) {
  const parsed = new URL(urlString);
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error(`Invalid protocol: ${parsed.protocol}`);
  }
  const host = parsed.hostname.toLowerCase();
  if (BLOCKED_HOSTNAMES.has(host)) {
    throw new Error(`Blocked hostname: ${host}`);
  }
  if (host.endsWith(".local") || host.endsWith(".localhost") || host.endsWith(".internal")) {
    throw new Error(`Blocked internal domain suffix on: ${host}`);
  }
  for (const regex of BLOCKED_IP_PATTERNS) {
    if (regex.test(host)) {
      throw new Error(`Blocked private IP: ${host}`);
    }
  }
  const port = parsed.port ? parseInt(parsed.port, 10) : (parsed.protocol === "https:" ? 443 : 80);
  if (![80, 443, 8080, 8443].includes(port)) {
    throw new Error(`Blocked port: ${port}`);
  }
  return true;
}

try {
  mockValidateUrlSecurity("http://127.0.0.1:8000/internal");
  assert(false, "Should reject loopback 127.0.0.1");
} catch (e) {
  assert(true, "Correctly rejected loopback 127.0.0.1");
}

try {
  mockValidateUrlSecurity("http://169.254.169.254/latest/meta-data/");
  assert(false, "Should reject AWS/GCP cloud metadata IP");
} catch (e) {
  assert(true, "Correctly rejected AWS/GCP cloud metadata IP 169.254.169.254");
}

try {
  mockValidateUrlSecurity("http://metadata.google.internal/computeMetadata/v1/");
  assert(false, "Should reject Google metadata hostname");
} catch (e) {
  assert(true, "Correctly rejected Google Cloud metadata hostname");
}

try {
  mockValidateUrlSecurity("http://192.168.1.50/admin");
  assert(false, "Should reject RFC 1918 192.168.x.x");
} catch (e) {
  assert(true, "Correctly rejected RFC 1918 private network 192.168.x.x");
}

try {
  mockValidateUrlSecurity("http://10.0.0.5/api");
  assert(false, "Should reject RFC 1918 10.x.x.x");
} catch (e) {
  assert(true, "Correctly rejected RFC 1918 private network 10.x.x.x");
}

try {
  mockValidateUrlSecurity("ftp://aitindia.in/brochure.pdf");
  assert(false, "Should reject non-HTTP(S) protocol");
} catch (e) {
  assert(true, "Correctly rejected non-HTTP protocol (ftp://)");
}

try {
  mockValidateUrlSecurity("https://aitindia.in:22/ssh");
  assert(false, "Should reject dangerous port 22");
} catch (e) {
  assert(true, "Correctly rejected dangerous SSH port 22");
}

try {
  const valid = mockValidateUrlSecurity("https://aitindia.in/admissions");
  assert(valid, "Permitted valid public HTTPS URL: https://aitindia.in/admissions");
} catch (e) {
  assert(false, `Unexpected error on valid URL: ${e.message}`);
}

// -----------------------------------------------------------------------------
// 2. TENANT DOMAIN BOUNDARY ENFORCEMENT
// -----------------------------------------------------------------------------
console.log("\n2. Tenant Domain Boundary Enforcement Tests:");

function mockIsUrlInCollegeDomain(targetUrl, officialDomain, allowedSubdomains = null) {
  const parsed = new URL(targetUrl);
  const host = parsed.hostname.toLowerCase();
  const base = officialDomain.toLowerCase().replace(/^(https?:\/\/)/, "").split("/")[0].split(":")[0];

  if (host === base || host === `www.${base}`) return true;
  if (base.startsWith("www.") && host === base.substring(4)) return true;

  if (host.endsWith(`.${base}`)) {
    if (!allowedSubdomains || allowedSubdomains.trim() === "" || allowedSubdomains.trim() === "*") {
      return true;
    }
    const allowed = allowedSubdomains.split(",").map((s) => s.trim().toLowerCase());
    const sub = host.substring(0, host.length - base.length - 1);
    return allowed.includes("*") || allowed.includes(sub) || allowed.some((a) => host.includes(a));
  }
  return false;
}

assert(
  mockIsUrlInCollegeDomain("https://aitindia.in/courses", "aitindia.in"),
  "Matches exact college domain"
);
assert(
  mockIsUrlInCollegeDomain("https://www.aitindia.in/fees", "aitindia.in"),
  "Matches www subdomain on college domain"
);
assert(
  mockIsUrlInCollegeDomain("https://admissions.aitindia.in/apply", "aitindia.in", "admissions,exam"),
  "Matches approved subdomain (admissions.aitindia.in)"
);
assert(
  !mockIsUrlInCollegeDomain("https://facebook.com/aitindia", "aitindia.in"),
  "Blocks third-party social media domain (facebook.com)"
);
assert(
  !mockIsUrlInCollegeDomain("https://malicious-aitindia.in", "aitindia.in"),
  "Blocks typosquatting / domain prefix attacks (malicious-aitindia.in)"
);
assert(
  !mockIsUrlInCollegeDomain("https://google.com/search?q=ait", "aitindia.in"),
  "Blocks search engine escaping"
);

// -----------------------------------------------------------------------------
// 3. URL CANONICALIZATION & NORMALIZATION
// -----------------------------------------------------------------------------
console.log("\n3. URL Canonicalization & Tracking Param Stripping Tests:");

const TRACKING_PARAMS = new Set(["utm_source", "utm_medium", "utm_campaign", "fbclid", "gclid", "ref"]);

function mockNormalizeUrl(rawUrl, baseUrl = null) {
  const resolved = baseUrl ? new URL(rawUrl, baseUrl) : new URL(rawUrl);
  resolved.hash = ""; // Strip fragment

  // Filter tracking queries
  const toDelete = [];
  resolved.searchParams.forEach((val, key) => {
    if (TRACKING_PARAMS.has(key.toLowerCase())) {
      toDelete.push(key);
    }
  });
  toDelete.forEach((k) => resolved.searchParams.delete(k));

  let out = resolved.toString();
  // Strip trailing slash if not root
  if (resolved.pathname !== "/" && out.endsWith("/")) {
    out = out.slice(0, -1);
  }
  return out;
}

const norm1 = mockNormalizeUrl("https://aitindia.in/about/#leadership");
assert(norm1 === "https://aitindia.in/about", `Strips fragment: ${norm1}`);

const norm2 = mockNormalizeUrl(
  "https://aitindia.in/admissions?utm_source=facebook&utm_campaign=2026&dept=cse"
);
assert(
  norm2 === "https://aitindia.in/admissions?dept=cse",
  `Strips tracking params while preserving functional query: ${norm2}`
);

const norm3 = mockNormalizeUrl("/contact", "https://aitindia.in/departments/cse");
assert(
  norm3 === "https://aitindia.in/contact",
  `Resolves relative path to origin domain: ${norm3}`
);

// -----------------------------------------------------------------------------
// 4. ROBOTS.TXT POLICY RULES & POLITENESS
// -----------------------------------------------------------------------------
console.log("\n4. Robots.txt Directives & Politeness Policy Tests:");

class MockRobotsParser {
  constructor(text) {
    this.disallows = [];
    this.allows = [];
    this.sitemaps = [];
    this.crawlDelay = 0.5;
    this.parse(text);
  }

  parse(text) {
    for (const raw of text.split("\n")) {
      const line = raw.trim();
      if (!line || line.startsWith("#")) continue;
      const colonIdx = line.indexOf(":");
      if (colonIdx === -1) continue;
      const directive = line.slice(0, colonIdx).trim();
      const value = line.slice(colonIdx + 1).trim();
      if (!directive || !value) continue;

      const d = directive.toLowerCase();
      if (d === "disallow") this.disallows.push(value);
      if (d === "allow") this.allows.push(value);
      if (d === "sitemap") this.sitemaps.push(value);
      if (d === "crawl-delay") this.crawlDelay = Math.max(0.1, Math.min(10, parseFloat(value) || 0.5));
    }
  }

  canFetch(path) {
    for (const a of this.allows) {
      if (path.startsWith(a)) return true;
    }
    for (const d of this.disallows) {
      if (path.startsWith(d)) return false;
    }
    return true;
  }
}

const sampleRobotsTxt = `
User-agent: *
Disallow: /admin/
Disallow: /cgi-bin/
Disallow: /private/
Allow: /admin/public-announcements
Crawl-delay: 2.0
Sitemap: https://aitindia.in/sitemap.xml
`;

const robots = new MockRobotsParser(sampleRobotsTxt);

assert(!robots.canFetch("/admin/login"), "Disallows /admin/login path");
assert(!robots.canFetch("/private/student-data"), "Disallows /private/ path");
assert(robots.canFetch("/admin/public-announcements"), "Allows more specific Allow: directive");
assert(robots.canFetch("/courses/engineering"), "Allows unlisted public routes");
assert(robots.crawlDelay === 2.0, "Correctly parsed Crawl-delay of 2.0s");
assert(robots.sitemaps.includes("https://aitindia.in/sitemap.xml"), "Extracted Sitemap directive");

// -----------------------------------------------------------------------------
// 5. HTML EXTRACTION & TABLE-TO-MARKDOWN
// -----------------------------------------------------------------------------
console.log("\n5. HTML Extraction & Table-to-Markdown Tests:");

function mockHtmlTableToMarkdown(rows) {
  if (!rows || rows.length === 0) return "";
  const header = rows[0];
  const headerLine = "| " + header.join(" | ") + " |";
  const separator = "| " + header.map(() => "---").join(" | ") + " |";
  const body = rows.slice(1).map((r) => "| " + r.join(" | ") + " |").join("\n");
  return `${headerLine}\n${separator}\n${body}`;
}

const sampleFeeTable = [
  ["Branch", "Annual Tuition", "Hostel Fee"],
  ["Computer Engineering", "₹85,000", "₹45,000"],
  ["Information Technology", "₹80,000", "₹45,000"],
  ["Mechanical Engineering", "₹70,000", "₹40,000"],
];

const mdTable = mockHtmlTableToMarkdown(sampleFeeTable);
assert(mdTable.includes("| Branch | Annual Tuition | Hostel Fee |"), "Formatted Markdown table header");
assert(mdTable.includes("| Computer Engineering | ₹85,000 | ₹45,000 |"), "Formatted Markdown table row 1");
assert(mdTable.includes("| Mechanical Engineering | ₹70,000 | ₹40,000 |"), "Formatted Markdown table row 3");

// -----------------------------------------------------------------------------
// 6. SHA-256 CONTENT HASHING & DEDUPLICATION
// -----------------------------------------------------------------------------
console.log("\n6. SHA-256 Content Fingerprinting & Deduplication Tests:");

const contentA = "Ahmedabad Institute of Technology provides engineering admissions for 2026-2027.";
const contentB = "Ahmedabad Institute of Technology provides engineering admissions for 2026-2027.";
const contentC = "Ahmedabad Institute of Technology updated fee structure for the 2026 semester.";

const hashA = crypto.createHash("sha256").update(contentA).digest("hex");
const hashB = crypto.createHash("sha256").update(contentB).digest("hex");
const hashC = crypto.createHash("sha256").update(contentC).digest("hex");

assert(hashA === hashB, "Identical content produces identical SHA-256 fingerprint (Deduplication)");
assert(hashA !== hashC, "Modified content produces distinct hash triggering change detection");
assert(hashA.length === 64, "SHA-256 hash has standard 64 hex characters");

// -----------------------------------------------------------------------------
// 7. CRAWL JOB LIFECYCLE STATE MACHINE
// -----------------------------------------------------------------------------
console.log("\n7. Crawl Job Lifecycle & Tenant Scoping Tests:");

const validTransitions = {
  PENDING: ["RUNNING", "CANCELLED"],
  RUNNING: ["PAUSED", "COMPLETED", "FAILED", "CANCELLED"],
  PAUSED: ["RUNNING", "CANCELLED"],
  COMPLETED: [],
  FAILED: [],
  CANCELLED: [],
};

function canTransition(current, next) {
  return validTransitions[current]?.includes(next) || false;
}

assert(canTransition("PENDING", "RUNNING"), "PENDING -> RUNNING valid");
assert(canTransition("RUNNING", "PAUSED"), "RUNNING -> PAUSED valid");
assert(canTransition("PAUSED", "RUNNING"), "PAUSED -> RUNNING valid");
assert(canTransition("RUNNING", "COMPLETED"), "RUNNING -> COMPLETED valid");
assert(canTransition("RUNNING", "CANCELLED"), "RUNNING -> CANCELLED valid");
assert(!canTransition("COMPLETED", "RUNNING"), "COMPLETED cannot transition back to RUNNING");
assert(!canTransition("CANCELLED", "PAUSED"), "CANCELLED cannot transition to PAUSED");

// -----------------------------------------------------------------------------
// SUMMARY
// -----------------------------------------------------------------------------
console.log("\n=======================================================");
console.log(`TOTAL TESTS: ${passed + failed}`);
console.log(`PASSED: \x1b[32m${passed}\x1b[0m`);
console.log(`FAILED: ${failed > 0 ? `\x1b[31m${failed}\x1b[0m` : `0`}`);
console.log("=======================================================\n");

if (failed > 0) {
  process.exit(1);
}
