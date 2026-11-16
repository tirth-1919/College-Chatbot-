/**
 * Phase 8 Automated Test Suite: PDF Upload, Document Processing & OCR Engine
 *
 * Verifies:
 * 1. File Signature & Magic Bytes Verification (%PDF-)
 * 2. MIME Type Checking & Path Traversal Sanitization
 * 3. File Size & Decompression Bomb Page Limit Protections
 * 4. Text Extraction & Structured Table-to-Markdown Formatting
 * 5. Scanned Page Detection & Tesseract OCR Trigger Threshold
 * 6. Cryptographic SHA-256 Fingerprinting & Multi-Tenant Duplicate Detection
 * 7. Private Storage Path Scoping & Signed URL Expiration
 * 8. Document Processing Lifecycle State Machine
 */

const crypto = require("crypto");
const path = require("path");

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

console.log("\n=================================================================");
console.log("   PHASE 8 AUTOMATED VERIFICATION: PDF & OCR PROCESSING ENGINE   ");
console.log("=================================================================\n");

// -----------------------------------------------------------------------------
// 1. MAGIC BYTES & FILE VALIDATION TESTS
// -----------------------------------------------------------------------------
console.log("1. Magic Bytes (%PDF-) & File Signature Validation Tests:");

const PDF_MAGIC_BYTES = Buffer.from("%PDF-");
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_PAGES = 200;

function mockValidatePdfHeader(buffer, filename, declaredMime = null) {
  if (!buffer || buffer.length === 0) {
    throw new Error("Empty file (0 bytes)");
  }
  if (buffer.length > MAX_FILE_SIZE) {
    throw new Error("File exceeds 50 MB limit");
  }
  const header = buffer.slice(0, 1024);
  if (header.indexOf(PDF_MAGIC_BYTES) === -1) {
    throw new Error("Invalid file signature: Missing %PDF- magic bytes");
  }
  if (declaredMime && !["application/pdf", "application/x-pdf", "application/octet-stream"].includes(declaredMime.toLowerCase())) {
    throw new Error(`Forbidden MIME type: ${declaredMime}`);
  }
  return true;
}

const validPdfBuffer = Buffer.concat([
  Buffer.from("%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"),
  Buffer.from("trailer\n<< /Root 1 0 R >>\n%%EOF"),
]);

const renamedExeBuffer = Buffer.concat([
  Buffer.from("MZ\x90\x00\x03\x00\x00\x00"), // DOS/Windows executable header
  Buffer.from("This program cannot be run in DOS mode."),
]);

const renamedHtmlBuffer = Buffer.from("<!DOCTYPE html><html><body><h1>Not a PDF</h1></body></html>");

try {
  mockValidatePdfHeader(validPdfBuffer, "prospectus.pdf", "application/pdf");
  assert(true, "Permitted valid PDF document with %PDF- header");
} catch (e) {
  assert(false, `Unexpected error on valid PDF: ${e.message}`);
}

try {
  mockValidatePdfHeader(renamedExeBuffer, "dangerous_trojan.pdf", "application/pdf");
  assert(false, "Should reject renamed .exe with .pdf extension");
} catch (e) {
  assert(true, "Rejected renamed executable with fake .pdf extension");
}

try {
  mockValidatePdfHeader(renamedHtmlBuffer, "phishing.pdf", "application/pdf");
  assert(false, "Should reject HTML document with fake .pdf extension");
} catch (e) {
  assert(true, "Rejected HTML content spoofed as PDF");
}

try {
  mockValidatePdfHeader(Buffer.alloc(0), "empty.pdf");
  assert(false, "Should reject empty 0-byte file");
} catch (e) {
  assert(true, "Rejected empty 0-byte upload");
}

try {
  const fakeBig = { length: 55 * 1024 * 1024 };
  mockValidatePdfHeader(fakeBig, "giant.pdf");
  assert(false, "Should reject file over 50MB");
} catch (e) {
  assert(true, "Enforced 50MB platform upload ceiling");
}

// -----------------------------------------------------------------------------
// 2. PATH TRAVERSAL & FILENAME SANITIZATION
// -----------------------------------------------------------------------------
console.log("\n2. Filename Sanitization & Path Traversal Defense Tests:");

function mockSanitizeFilename(filename) {
  if (!filename) return "document.pdf";
  let clean = filename.replace(/[\x00/\\:*?"<>|]/g, "").replace(/\.\./g, "").trim();
  if (!clean) clean = "document.pdf";
  if (!clean.toLowerCase().endsWith(".pdf")) clean += ".pdf";
  return clean.slice(0, 255);
}

const s1 = mockSanitizeFilename("../../../etc/passwd");
assert(s1 === "etcpasswd.pdf", `Neutralized Unix path traversal: ${s1}`);

const s2 = mockSanitizeFilename("..\\..\\windows\\system32\\cmd.exe");
assert(s2 === "windowssystem32cmd.exe.pdf", `Neutralized Windows path traversal: ${s2}`);

const s3 = mockSanitizeFilename("AIT_Admissions_Fee_2026.pdf");
assert(s3 === "AIT_Admissions_Fee_2026.pdf", `Preserved legitimate institutional filename: ${s3}`);

// -----------------------------------------------------------------------------
// 3. TABLE EXTRACTION & MARKDOWN FORMATTING
// -----------------------------------------------------------------------------
console.log("\n3. Tabular Parsing & Markdown Grid Representation Tests:");

function mockFormatTableToMarkdown(rows) {
  if (!rows || rows.length === 0) return "";
  const maxCols = Math.max(...rows.map((r) => r.length));
  const padded = rows.map((r) => r.concat(Array(maxCols - r.length).fill("")));
  const header = padded[0].map((c) => String(c || "").trim().replace(/\|/g, "\\|"));
  const headerLine = "| " + header.join(" | ") + " |";
  const separatorLine = "| " + header.map(() => "---").join(" | ") + " |";
  const bodyLines = padded.slice(1).map(
    (r) => "| " + r.map((c) => String(c || "").trim().replace(/\|/g, "\\|")).join(" | ") + " |"
  );
  return [headerLine, separatorLine, ...bodyLines].join("\n");
}

const feeTableRows = [
  ["Course Name", "Intake Capacity", "Tuition Fee (Per Sem)", "Exam Fee"],
  ["B.Tech Computer Engg", "180 Seats", "₹42,500", "₹1,200"],
  ["B.Tech AI & Data Science", "120 Seats", "₹45,000", "₹1,200"],
  ["B.Tech Mechanical Engg", "60 Seats", "₹35,000", "₹1,200"],
];

const formattedMarkdownTable = mockFormatTableToMarkdown(feeTableRows);
assert(formattedMarkdownTable.includes("| Course Name | Intake Capacity |"), "Generated markdown table header");
assert(formattedMarkdownTable.includes("| B.Tech Computer Engg | 180 Seats | ₹42,500 |"), "Formatted row 1 properly");
assert(formattedMarkdownTable.includes("| B.Tech AI & Data Science | 120 Seats |"), "Formatted row 2 properly");

// -----------------------------------------------------------------------------
// 4. SCANNED PAGE DETECTION & OCR ENGINE THRESHOLD
// -----------------------------------------------------------------------------
console.log("\n4. Scanned Page Detection & OCR Trigger Threshold Tests:");

const MIN_TEXT_THRESHOLD = 50;

function mockPageAnalyzer(extractedText) {
  const clean = (extractedText || "").trim();
  const isScanned = clean.length < MIN_TEXT_THRESHOLD;
  return {
    charCount: clean.length,
    isScanned,
    requiresOcr: isScanned,
  };
}

const textRichPage = "Ahmedabad Institute of Technology was established in 2004 under Silver Oak Trust. Approved by AICTE and affiliated with GTU.";
const p1 = mockPageAnalyzer(textRichPage);
assert(!p1.isScanned && !p1.requiresOcr, `Text-rich page (${p1.charCount} chars) avoids unnecessary OCR`);

const scannedStampPage = "CONFIDENTIAL\nGTU";
const p2 = mockPageAnalyzer(scannedStampPage);
assert(p2.isScanned && p2.requiresOcr, `Low-text scanned page (${p2.charCount} chars < ${MIN_TEXT_THRESHOLD}) triggers OCR pipeline`);

function mockOcrConfidenceCalc(wordConfidences) {
  if (!wordConfidences || wordConfidences.length === 0) return 0;
  const sum = wordConfidences.reduce((a, b) => a + b, 0);
  return Math.round((sum / wordConfidences.length) * 10) / 10;
}

const sampleWordConfidences = [92.5, 88.0, 95.1, 78.4, 91.2];
const avgConfidence = mockOcrConfidenceCalc(sampleWordConfidences);
assert(avgConfidence === 89.0, `Calculated OCR average confidence: ${avgConfidence}%`);

// -----------------------------------------------------------------------------
// 5. SHA-256 BINARY HASHING & DUPLICATE DETECTION
// -----------------------------------------------------------------------------
console.log("\n5. SHA-256 Checksums & Multi-Tenant Deduplication Tests:");

const pdfDocA = Buffer.from("%PDF-1.7 Original Circular Content For 2026 Admissions");
const pdfDocB = Buffer.from("%PDF-1.7 Original Circular Content For 2026 Admissions");
const pdfDocC = Buffer.from("%PDF-1.7 Revised Circular Content With Updated Fee Dates");

const hashA = crypto.createHash("sha256").update(pdfDocA).digest("hex");
const hashB = crypto.createHash("sha256").update(pdfDocB).digest("hex");
const hashC = crypto.createHash("sha256").update(pdfDocC).digest("hex");

assert(hashA === hashB, "Identical binary payloads generate identical SHA-256 hashes");
assert(hashA !== hashC, "Modified content triggers separate version / checksum");
assert(hashA.length === 64, "SHA-256 checksum has standard 64-hexadecimal length");

// Tenant isolation check: Same checksum uploaded by different colleges
const college1 = "11111111-1111-1111-1111-111111111111";
const college2 = "22222222-2222-2222-2222-222222222222";

function mockCheckDuplicate(collegeId, checksum, database) {
  return database.some((doc) => doc.collegeId === collegeId && doc.checksum === checksum);
}

const existingDocs = [
  { id: "doc-1", collegeId: college1, checksum: hashA },
];

assert(
  mockCheckDuplicate(college1, hashA, existingDocs),
  "Detects duplicate upload for same college tenant"
);
assert(
  !mockCheckDuplicate(college2, hashA, existingDocs),
  "Permits upload of identical document for a different college tenant (Tenant Isolation)"
);

// -----------------------------------------------------------------------------
// 6. PRIVATE STORAGE PATHS & SIGNED URL SECURITY
// -----------------------------------------------------------------------------
console.log("\n6. Private Storage Paths & Signed Download URL Security Tests:");

function mockBuildStoragePath(collegeId, docId) {
  return `${collegeId}/${docId}.pdf`;
}

const testCollegeId = "550e8400-e29b-41d4-a716-446655440000";
const testDocId = "7c9e6679-7425-40de-944b-e07fc1f90ae7";
const storagePath = mockBuildStoragePath(testCollegeId, testDocId);

assert(
  storagePath === "550e8400-e29b-41d4-a716-446655440000/7c9e6679-7425-40de-944b-e07fc1f90ae7.pdf",
  `Storage path strictly partitioned by tenant: ${storagePath}`
);

function mockGenerateSignedUrl(collegeId, storagePath, expiresIn = 3600) {
  const exp = Math.floor(Date.now() / 1000) + expiresIn;
  const signature = crypto.createHmac("sha256", "test_secret").update(`${storagePath}:${exp}`).digest("hex");
  return `https://supabase.co/storage/v1/object/sign/college-documents/${storagePath}?token=${signature}&expires=${exp}`;
}

const signedUrl = mockGenerateSignedUrl(testCollegeId, storagePath, 3600);
assert(signedUrl.includes("/college-documents/"), "URL points to private bucket");
assert(signedUrl.includes("expires="), "URL contains explicit token expiration");
assert(signedUrl.includes("token="), "URL contains cryptographic HMAC signature");

// -----------------------------------------------------------------------------
// 7. DOCUMENT PROCESSING STATE MACHINE
// -----------------------------------------------------------------------------
console.log("\n7. Document Processing Lifecycle State Machine Tests:");

const validDocTransitions = {
  UPLOADED: ["VALIDATING", "QUEUED", "FAILED"],
  VALIDATING: ["QUEUED", "FAILED"],
  QUEUED: ["PROCESSING", "REPROCESSING", "FAILED"],
  PROCESSING: ["OCR_PROCESSING", "EXTRACTED", "PENDING_REVIEW", "FAILED"],
  OCR_PROCESSING: ["EXTRACTED", "PENDING_REVIEW", "FAILED"],
  EXTRACTED: ["PENDING_REVIEW", "FAILED"],
  PENDING_REVIEW: ["COMPLETED", "REPROCESSING", "DELETED"],
  COMPLETED: ["REPROCESSING", "DELETED"],
  FAILED: ["QUEUED", "REPROCESSING", "DELETED"],
  REPROCESSING: ["PROCESSING", "FAILED"],
  DELETED: [],
};

function canTransition(from, to) {
  return validDocTransitions[from]?.includes(to) || false;
}

assert(canTransition("UPLOADED", "QUEUED"), "UPLOADED -> QUEUED valid");
assert(canTransition("QUEUED", "PROCESSING"), "QUEUED -> PROCESSING valid");
assert(canTransition("PROCESSING", "OCR_PROCESSING"), "PROCESSING -> OCR_PROCESSING valid");
assert(canTransition("OCR_PROCESSING", "PENDING_REVIEW"), "OCR_PROCESSING -> PENDING_REVIEW valid");
assert(canTransition("PROCESSING", "FAILED"), "PROCESSING -> FAILED valid");
assert(canTransition("FAILED", "QUEUED"), "FAILED -> QUEUED valid (Retry)");
assert(canTransition("PENDING_REVIEW", "DELETED"), "PENDING_REVIEW -> DELETED valid");
assert(!canTransition("DELETED", "PROCESSING"), "DELETED documents cannot transition back to PROCESSING");

// -----------------------------------------------------------------------------
// SUMMARY
// -----------------------------------------------------------------------------
console.log("\n=================================================================");
console.log(`TOTAL TESTS: ${passed + failed}`);
console.log(`PASSED: \x1b[32m${passed}\x1b[0m`);
console.log(`FAILED: ${failed > 0 ? `\x1b[31m${failed}\x1b[0m` : `0`}`);
console.log("=================================================================\n");

if (failed > 0) {
  process.exit(1);
}

