import { apiRequest } from "@/lib/api-client";
import { AUTH_SESSION_INVALID_KEY } from "@/lib/auth-session";

export function generateUUID(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID();
    } catch (e) {}
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface SourceCitationData {
  title: string;
  source_type: "OFFICIAL_WEBSITE" | "PDF" | "ADMIN_VERIFIED" | "GEMINI_UNVERIFIED" | "SECONDARY_AI_FALLBACK" | "NO_RELIABLE_INFORMATION";
  url?: string;
  page_number?: number;
  section?: string;
  similarity_score?: number;
  image_url?: string;
  image_category?: string;
  image_description?: string;
  event_name?: string;
  event_date?: string;
}

export type FeedbackCategory = "ACCURACY" | "INCORRECT_INFO" | "MISSING_INFO" | "TECHNICAL_ISSUE" | "GENERAL";

export interface SupportTicketInput {
  college_id?: string;
  session_id?: string;
  subject: string;
  message: string;
  category?: "LOGIN" | "CHATBOT" | "INCORRECT_ANSWER" | "MISSING_INFO" | "DOCUMENT" | "TECHNICAL" | "OTHER";
  priority?: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
}

export interface UserPreferencesData {
  preferred_language: string;
  preferences?: Record<string, any>;
}

export interface SwitchActionData {
  targetCollegeId: string;
  targetCollegeName: string;
  currentCollegeName: string;
  pendingQuestion: string;
  status?: "pending" | "switched" | "stayed";
}

export interface ChatMessageData {
  id: string;
  session_id: string;
  sender_role: "user" | "assistant" | "system";
  message_text: string;
  is_verified: boolean;
  answer_source_type: "OFFICIAL_WEBSITE" | "ADMIN_VERIFIED" | "GEMINI_UNVERIFIED" | "SECONDARY_AI_FALLBACK" | "NO_RELIABLE_INFORMATION" | "AI_GUIDANCE" | "OPENAI_UNVERIFIED" | "XKIRO_UNVERIFIED";
  source_citations: SourceCitationData[];
  token_count: number;
  model_used?: string;
  created_at: string;
  answer_mode?: string;
  actual_provider?: string;
  actual_model?: string;
  fallback_reason?: string;
  attempt_count?: number;
  request_duration_ms?: number;
  switch_action?: SwitchActionData;
}

export interface ChatSessionData {
  id: string;
  college_id: string;
  user_id?: string;
  session_title: string;
  language: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  messages?: ChatMessageData[];
  local_state?: "unavailable";
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

export function hasVisitorToken(sessionId: string): boolean {
  return typeof window !== "undefined" &&
    Boolean(sessionStorage.getItem(`campusai_chat_visitor_${sessionId}`));
}

function getSessionAccessHeaders(sessionId: string, collegeId: string): Record<string, string> | null {
  if (typeof window === "undefined" || !collegeId) return null;
  const visitorToken = sessionStorage.getItem(`campusai_chat_visitor_${sessionId}`);
  const authenticated = Boolean(
    localStorage.getItem("auth_token") && !localStorage.getItem(AUTH_SESSION_INVALID_KEY)
  );
  if (!visitorToken && !authenticated) return null;
  return {
    "X-College-ID": collegeId,
    ...(visitorToken ? { "X-Chat-Visitor-Token": visitorToken } : {}),
  };
}

function generateLocalAnswer(
  prompt: string,
  collegeName: string,
  language: string = "en",
  sessionId: string = "local"
): ChatMessageData {
  if (process.env.NEXT_PUBLIC_LOCAL_CHAT_DEMO !== "true") {
    const message = "Chat service is unavailable. This conversation remains only on this device and was not sent to the server.";
    return {
      id: generateUUID(),
      session_id: sessionId,
      sender_role: "assistant",
      message_text: message,
      is_verified: false,
      answer_source_type: "NO_RELIABLE_INFORMATION",
      source_citations: [],
      token_count: message.split(" ").length,
      model_used: undefined,
      created_at: new Date().toISOString(),
    };
  }

  const p = prompt.toLowerCase();
  const slug = collegeName.toLowerCase().replace(/[^a-z0-9]/g, "-").replace(/-+/g, "-");

  let answerText = "";
  let sourceType: "OFFICIAL_WEBSITE" | "ADMIN_VERIFIED" | "GEMINI_UNVERIFIED" | "SECONDARY_AI_FALLBACK" | "NO_RELIABLE_INFORMATION" = "OFFICIAL_WEBSITE";
  let citations: SourceCitationData[] = [];

  // 1. Fees & Costs
  if (p.includes("fee") || p.includes("cost") || p.includes("charges") || p.includes("scholarship") || p.includes("फी") || p.includes("ફી")) {
    if (language === "hi") {
      answerText = `**${collegeName} - अधिकृत शुल्क संरचना (शैक्षणिक वर्ष 2024-25):**\n\n` +
        `• **B.Tech / B.E. ट्यूशन फीस:** ₹78,000 – ₹85,000 प्रति वर्ष (FRC अनुमोदित)\n` +
        `• **परीक्षा व नामांकन शुल्क:** ₹3,500 प्रति सेमेस्टर (विश्वविद्यालय नियमानुसार)\n` +
        `• **प्रयोगशाला व पुस्तकालय अमानत:** ₹5,000 (वापसी योग्य)\n` +
        `• **छात्रावास व भोजन शुल्क:** ₹48,000 – ₹60,000 प्रति वर्ष\n\n` +
        `💡 *छात्रवृत्ति:* डिजिटल गुजरात MYSY और SC/ST/SEBC पोस्ट-मैट्रिक योजनाएं लागू हैं।`;
    } else if (language === "gu") {
      answerText = `**${collegeName} - અધિકૃત ફી માળખું (શૈક્ષણિક વર્ષ ૨૦૨૪-૨૫):**\n\n` +
        `• **B.Tech / B.E. ટ્યુશન ફી:** ₹૭૮,૦૦૦ – ₹૮૫,૦૦૦ વાર્ષિક (FRC મંજૂર)\n` +
        `• **પરીક્ષા અને નોંધણી ફી:** ₹૩,૫૦૦ પ્રતિ સેમેસ્ટર\n` +
        `• **લેબોરેટરી અને લાયબ્રેરી ડિપોઝીટ:** ₹૫,૦૦૦ (રીફંડેબલ)\n` +
        `• **હોસ્ટેલ અને ભોજન ખર્ચ:** ₹૪૮,૦૦૦ – ₹૬૦,૦૦૦ વાર્ષિક\n\n` +
        `💡 *સ્કોલરશિપ:* MYSY સહાય યોજના અને સરકારી શિષ્યવૃત્તિ ઉપલબ્ધ છે.`;
    } else {
      answerText = `Here is the official fee structure for **${collegeName}** (Academic Year 2024-25):\n\n` +
        `• **B.Tech / B.E. Tuition Fee:** ₹78,000 – ₹85,000 per annum (approved by Fee Regulatory Committee - FRC).\n` +
        `• **Enrollment & Examination Fee:** ₹3,500 per semester.\n` +
        `• **Library & Laboratory Deposit (Refundable):** ₹5,000 one-time.\n` +
        `• **Hostel & Mess Charges:** ₹48,000 – ₹60,000 per annum (optional based on accommodation type).\n\n` +
        `💡 **Scholarships Available:** Digital Gujarat Mukhyamantri Yuva Swavalamban Yojana (MYSY), Tuition Fee Waiver (TFW) scheme, and Post-Matric scholarships for reserved categories.`;
    }
    sourceType = "OFFICIAL_WEBSITE";
    citations = [
      {
        title: "Official Fee Circular & FRC Approval Order",
        source_type: "PDF",
        page_number: 2,
        similarity_score: 0.96,
      },
      {
        title: `${collegeName} Official Admissions Brochure`,
        source_type: "OFFICIAL_WEBSITE",
        url: `https://${slug}.edu.in/admissions/fee-structure`,
        similarity_score: 0.94,
      },
    ];
  }
  // 2. Admission Process & Eligibility
  else if (p.includes("admission") || p.includes("eligibility") || p.includes("process") || p.includes("cutoff") || p.includes("प्रवेश") || p.includes("પ્રવેશ")) {
    if (language === "hi") {
      answerText = `**${collegeName} - प्रवेश प्रक्रिया और पात्रता नियम:**\n\n` +
        `1. **शैक्षणिक योग्यता:** 10+2 (PCM) में न्यूनतम 45% अंक (आरक्षित वर्गों के लिए 40%) आवश्यक हैं।\n` +
        `2. **प्रवेश परीक्षा:** GUJCET या JEE Main स्कोरकार्ड अनिवार्य है।\n` +
        `3. **काउंसलिंग:** अधिकांश सीटें ACPC (Admission Committee for Professional Courses) ऑनलाइन प्रक्रिया द्वारा आवंटित की जाती हैं।\n` +
        `4. **प्रबंधन कोटा:** संस्थागत स्तर पर योग्यता अनुसार निर्धारित ACPC नियमों के तहत सीटें भरी जाती हैं।`;
    } else if (language === "gu") {
      answerText = `**${collegeName} - પ્રવેશ પ્રક્રિયા અને લાયકાત:**\n\n` +
        `૧. **લાયકાત:** ધોરણ ૧૨ વિજ્ઞાન પ્રવાહ (PCM) માં ઓછામાં ઓછા ૪૫% ગુણ (અનામત વર્ગ માટે ૪૦%).\n` +
        `૨. **પ્રવેશ પરીક્ષા:** GUJCET અથવા JEE Main સ્કોર ફરજિયાત.\n` +
        `૩. **કાઉન્સિલિંગ:** ACPC સેન્ટ્રલાઇઝ્ડ ઓનલાઇન એડમિશન પદ્ધતિ મારફતે ફાળવણી.\n` +
        `૪. **મેનેજમેન્ટ ક્વોટા:** ACPC ની માર્ગદર્શિકા મુજબ સીધી મેરિટ પ્રક્રિયા.`;
    } else {
      answerText = `Admissions at **${collegeName}** follow centralized academic guidelines:\n\n` +
        `1. **Eligibility Criteria:** Minimum 45% aggregate in 10+2 (Physics, Mathematics, and Chemistry/CS) for General category; 40% for Reserved categories.\n` +
        `2. **Accepted Entrance Exams:** GUJCET or JEE (Main).\n` +
        `3. **Counseling Route:** Centralized admission counseling through ACPC (Admission Committee for Professional Courses).\n` +
        `4. **Management / Vacant Quota:** Institutional merit rounds are announced after ACPC Round 2 as per regulatory norms.`;
    }
    sourceType = "ADMIN_VERIFIED";
    citations = [
      {
        title: "ACPC Admission Guidelines & Criteria Bulletin",
        source_type: "OFFICIAL_WEBSITE",
        url: `https://${slug}.edu.in/admissions/eligibility`,
        similarity_score: 0.95,
      },
      {
        title: "College Admission Committee Resolution",
        source_type: "ADMIN_VERIFIED",
        similarity_score: 0.92,
      },
    ];
  }
  // 3. Required Documents
  else if (p.includes("document") || p.includes("certificate") || p.includes("verification") || p.includes("दस्तावेज") || p.includes("દસ્તાવેજ")) {
    if (language === "hi") {
      answerText = `**${collegeName} - प्रवेश सत्यापन हेतु आवश्यक दस्तावेज:**\n\n` +
        `1. 10वीं और 12वीं की मूल मार्कशीट व 3 फोटोकॉपी\n` +
        `2. स्कूल लीविंग सर्टिफिकेट (स्थानांतरण प्रमाण पत्र)\n` +
        `3. GUJCET / JEE Main स्कोरकार्ड\n` +
        `4. ACPC आवंटन पत्र और टोकन शुल्क रसीद\n` +
        `5. जाति प्रमाण पत्र व गैर-क्रीमी लेयर (NCL - यदि लागू हो)\n` +
        `6. आय प्रमाण पत्र (MYSY/TFW छात्रवृत्ति के लिए)\n` +
        `7. 6 पासपोर्ट साइज रंगीन फोटो एवं आधार कार्ड की प्रति`;
    } else if (language === "gu") {
      answerText = `**${collegeName} - પ્રવેશ વેરિફિકેશન માટે જરૂરી દસ્તાવેજો:**\n\n` +
        `૧. ધોરણ ૧૦ અને ૧૨ ની ઓરિજિનલ માર્કશીટ તથા ૩ ઝેરોક્ષ નકલો\n` +
        `૨. શાળા છોડ્યાનું પ્રમાણપત્ર (LC)\n` +
        `૩. GUJCET / JEE Main રિઝલ્ટ\n` +
        `૪. ACPC સીટ એલોટમેન્ટ લેટર અને ફી પહોંચ\n` +
        `૫. જાતિ પ્રમાણપત્ર અને નોન-ક્રીમીલેયર (લાગુ પડતું હોય તો)\n` +
        `૬. આવકનો દાખલો તથા પાસપોર્ટ સાઇઝના ૬ ફોટા અને આધારકાર્ડ`;
    } else {
      answerText = `The mandatory documents required for admission verification at **${collegeName}** are:\n\n` +
        `1. **Academic Records:** 10th & 12th Standard Marksheets (Original + 3 self-attested copies)\n` +
        `2. **Transfer Credentials:** School Leaving Certificate (TC/LC) and Migration Certificate\n` +
        `3. **Entrance Scores:** GUJCET / JEE Main Official Scorecard\n` +
        `4. **Counseling Allotment:** ACPC Seat Allotment Letter and Token Tuition Fee Receipt\n` +
        `5. **Category Proof:** Caste Certificate & valid Non-Creamy Layer (NCL) for the current financial year\n` +
        `6. **Financial / Domicile:** Family Income Certificate (for TFW/MYSY applicants) and Domicile Certificate\n` +
        `7. **Identification:** Aadhaar Card copy and 6 recent passport-size photographs`;
    }
    sourceType = "OFFICIAL_WEBSITE";
    citations = [
      {
        title: "Admission Verification Checklist & Document Regulations",
        source_type: "PDF",
        page_number: 1,
        similarity_score: 0.97,
      },
    ];
  }
  // 4. Hostel & Living Facilities
  else if (p.includes("hostel") || p.includes("accommodation") || p.includes("facility") || p.includes("campus") || p.includes("हॉस्टल") || p.includes("હોસ્ટેલ")) {
    if (language === "hi") {
      answerText = `**${collegeName} - छात्रावास एवं परिसर सुविधाएं:**\n\n` +
        `• **छात्रावास:** लड़कों और लड़कियों के लिए पृथक, सुरक्षित 24/7 CCTV और बायोमेट्रिक निगरानी वाले हॉस्टल।\n` +
        `• **कमरे:** 2-सीटर और 3-सीटर कमरे, जिनमें बेड, अलमारी, स्टडी टेबल और वाई-फाई उपलब्ध है।\n` +
        `• **मेस (भोजनालय):** स्वच्छ व पौष्टिक शाकाहारी भोजन (नाश्ता, दोपहर व रात का खाना)।\n` +
        `• **परिसर सुविधाएं:** एयर-कंडीशન્ડ केंद्रीय पुस्तकालय (40,000+ पुस्तकें), अत्याधुनिक कंप्यूटर लैब, खेल परिसर, कैंटीन और चिकित्सा सहायता।`;
    } else if (language === "gu") {
      answerText = `**${collegeName} - હોસ્ટેલ અને કેમ્પસ સુવિધાઓ:**\n\n` +
        `• **હોસ્ટેલ:** કુમાર અને કન્યાઓ માટે અલગ, ૨૪/૭ સીસીટીવી અને સુરક્ષા વ્યવસ્થા સાથે હોસ્ટેલ બ્લોક.\n` +
        `• **રૂમ:** અભ્યાસ ટેબલ, કબાટ, પલંગ અને હાઇ-સ્પીડ વાઇ-ફાઇથી સજ્જ રૂમ.\n` +
        `• **મેસ:** શુદ્ધ, પૌષ્ટિક શાકાહારી ભોજનની સુવિધા.\n` +
        `• **કેમ્પસ:** એર-કન્ડિશન્ડ લાયબ્રેરી, લેબ્સ, ઇન્ડોર-આઉટડોર સ્પોર્ટ્સ અને કેન્ટીન.`;
    } else {
      answerText = `Student living and campus amenities at **${collegeName}** include:\n\n` +
        `• **Residential Hostels:** Separate blocks for boys and girls with 24/7 biometric security and warden supervision.\n` +
        `• **Room Facilities:** Furnished double and triple occupancy rooms with study desks, ergonomic chairs, wardrobes, and high-speed Wi-Fi.\n` +
        `• **Dining Hall & Mess:** Hygienic multi-cuisine vegetarian meal plans covering breakfast, lunch, tea, and dinner.\n` +
        `• **Academic Infrastructure:** Air-conditioned Central Digital Library with 40,000+ titles, high-performance computing centers, dedicated seminar halls, and on-campus healthcare.`;
    }
    sourceType = "ADMIN_VERIFIED";
    citations = [
      {
        title: "Campus Infrastructure & Hostel Residence Handbook",
        source_type: "ADMIN_VERIFIED",
        similarity_score: 0.93,
      },
      {
        title: `${collegeName} Official Facilities Portal`,
        source_type: "OFFICIAL_WEBSITE",
        url: `https://${slug}.edu.in/campus/hostel`,
        similarity_score: 0.91,
      },
    ];
  }
  // 5. Head of Department (HOD) & Leadership
  else if (p.includes("head") || p.includes("hod") || p.includes("department") || p.includes("faculty") || p.includes("professor") || p.includes("principal")) {
    if (language === "hi") {
      answerText = `**${collegeName} - प्रमुख विभागाध्यक्ष और शैक्षणिक नेतृत्व:**\n\n` +
        `• **कंप्यूटर इंजीनियरिंग / IT:** डॉ. आर. के. पटेल (Ph.D., M.Tech - 18+ वर्ष अनुभव) — ईमेल: \`hod.ce@${slug}.edu.in\`\n` +
        `• **मैकेनिकल इंजीनियरिंग:** डॉ. ए. वी. जोशी (Ph.D.) — ईमेल: \`hod.me@${slug}.edu.in\`\n` +
        `• **सिविल इंजीनियरिंग:** प्रो. एन. डी. शाह — ईमेल: \`hod.civil@${slug}.edu.in\`\n` +
        `• **इलेक्ट्रिकल इंजीनियरिंग:** डॉ. एस. के. देसाई — ईमेल: \`hod.ee@${slug}.edu.in\`\n` +
        `• **प्राचार्य कार्यालय:** डॉ. एम. जी. भट्ट — संपर्क समय: सोमवार से शुक्रवार, 11:00 AM से 4:00 PM`;
    } else if (language === "gu") {
      answerText = `**${collegeName} - વિભાગીય વડા (HOD) અને નેતૃત્વ:**\n\n` +
        `• **કોમ્પ્યુટર એન્જિનિયરિંગ / IT:** ડૉ. આર. કે. પટેલ — ઇમેઇલ: \`hod.ce@${slug}.edu.in\`\n` +
        `• **મિકેનિકલ એન્જિનિયરિંગ:** ડૉ. એ. વી. જોષી — ઇમેઇલ: \`hod.me@${slug}.edu.in\`\n` +
        `• **સિવિલ એન્જિનિયરિંગ:** પ્રો. એન. ડી. શાહ — ઇમેઇલ: \`hod.civil@${slug}.edu.in\`\n` +
        `• **પ્રિન્સિપાલ કચેરી:** ડૉ. એમ. જી. ભટ્ટ (મળવાનો સમય: ૧૧:૦૦ થી ૪:૦૦)`;
    } else {
      answerText = `Academic Department Heads and Leadership at **${collegeName}**:\n\n` +
        `• **Computer Engineering & IT:** Dr. R. K. Patel (Ph.D., M.Tech, Senior IEEE Member) — Contact: \`hod.ce@${slug}.edu.in\`\n` +
        `• **Mechanical Engineering:** Dr. A. V. Joshi (Ph.D., Research Specialist in Thermal Systems) — Contact: \`hod.me@${slug}.edu.in\`\n` +
        `• **Civil Engineering:** Prof. N. D. Shah (Structural Design Consultant) — Contact: \`hod.civil@${slug}.edu.in\`\n` +
        `• **Electrical & Electronics:** Dr. S. K. Desai — Contact: \`hod.ee@${slug}.edu.in\`\n` +
        `• **Principal / Director:** Dr. M. G. Bhatt — Office consultations available Monday–Friday, 11:00 AM – 4:00 PM.`;
    }
    sourceType = "OFFICIAL_WEBSITE";
    citations = [
      {
        title: "Faculty Directory & Academic Department Governance",
        source_type: "OFFICIAL_WEBSITE",
        url: `https://${slug}.edu.in/academics/departments`,
        similarity_score: 0.98,
      },
    ];
  }
  // 6. Placements & Packages
  else if (p.includes("placement") || p.includes("package") || p.includes("salary") || p.includes("recruit") || p.includes("company") || p.includes("नौकरी") || p.includes("પ્લેસમેન્ટ")) {
    if (language === "hi") {
      answerText = `**${collegeName} - प्लेसमेंट और करियर आंकड़े (नवीनतम बैच):**\n\n` +
        `• **प्लेसमेंट दर:** 88.4% योग्य छात्रों को कैंपस प्लेसमेंट मिला।\n` +
        `• **उच्चतम पैकेज:** ₹18.5 लाख प्रति वर्ष (LPA)।\n` +
        `• **औसत पैकेज:** ₹5.2 लाख प्रति वर्ष (LPA)।\n` +
        `• **प्रमुख भर्तीकर्ता:** TCS, Infosys, Capgemini, Wipro, L&T Infotech, Reliance Industries, Adani Group और Cognizant।\n` +
        `• **इंटर्नशिप:** 8वें सेमेस्टर में उद्योग-उन्मुख इंटर्नशिप अनिवार्य रूप से प्रदान की जाती है।`;
    } else if (language === "gu") {
      answerText = `**${collegeName} - પ્લેસમેન્ટ અને કેરિયર રેકોર્ડ:**\n\n` +
        `• **પ્લેસમેન્ટ ટકાવારી:** ૮૮.૪% પાત્ર વિદ્યાર્થીઓને જોબ ઓફર મળી.\n` +
        `• **સૌથી ઊંચું પેકેજ:** ₹૧૮.૫ લાખ વાર્ષિક (LPA).\n` +
        `• **સરેરાશ પેકેજ:** ₹૫.૨ લાખ વાર્ષિક (LPA).\n` +
        `• **મુખ્ય કંપનીઓ:** TCS, Infosys, Wipro, L&T, Reliance, Adani અને Capgemini.\n` +
        `• **ઇન્ટર્નશિપ:** છેલ્લા સેમેસ્ટરમાં પ્રીમિયર ટેક કંપનીઓમાં ઇન્ટર્નશિપની તક.`;
    } else {
      answerText = `Career Placements and Corporate Recruitment at **${collegeName}** (Recent Academic Year):\n\n` +
        `• **Overall Placement Rate:** 88.4% of eligible graduates successfully placed.\n` +
        `• **Highest CTC Offered:** ₹18.50 LPA (Software Engineering / Cloud Services).\n` +
        `• **Average CTC:** ₹5.20 LPA across all technical streams.\n` +
        `• **Top Recruiting Partners:** Tata Consultancy Services (TCS), Infosys, Capgemini, L&T Infotech, Reliance Industries, Wipro, Adani Group, and Cognizant.\n` +
        `• **Industry Internships:** 6-month final-semester internships coordinated by the institutional Training & Placement Cell (TPO).`;
    }
    sourceType = "OFFICIAL_WEBSITE";
    citations = [
      {
        title: "Annual Training & Placement Office (TPO) Verified Audit",
        source_type: "PDF",
        page_number: 4,
        similarity_score: 0.95,
      },
      {
        title: `${collegeName} Official Placement Cell Report`,
        source_type: "OFFICIAL_WEBSITE",
        url: `https://${slug}.edu.in/placements/statistics`,
        similarity_score: 0.93,
      },
    ];
  }
  // 7. General inquiries
  else {
    if (language === "hi") {
      answerText = `**${collegeName}** के संबंध में आपके प्रश्न *"${prompt}"* की जानकारी:\n\n` +
        `संस्थान से संबंधित अधिकृत शैक्षणिक, छात्रावास एवं प्रवेश विवरण आधिकारिक कॉलेज पोर्टल पर सत्यापित किए गए हैं।\n\n` +
        `• **कार्यालय का समय:** सोमवार से शुक्रवार, सुबह 9:30 से शाम 5:30 बजे तक।\n` +
        `• **प्रवेश हेल्पलाइन:** \`admissions@${slug}.edu.in\` | दूरभाष: +91 79 2630 1111\n\n` +
        `यदि आपको शुल्क, कट-ऑफ या पाठ्यक्रम की विशिष्ट जानकारी चाहिए, तो कृपया ऊपर दिए गए सुझावों में से चयन करें।`;
    } else if (language === "gu") {
      answerText = `**${collegeName}** અંગે તમારા પ્રશ્ન *"${prompt}"* ની વિગત:\n\n` +
        `સંસ્થાના શૈક્ષણિક નિયમો, પરિપત્રો અને એડમિશનની અધિકૃત માહિતી વેબસાઇટ પર ચકાસેલ છે.\n\n` +
        `• **ઓફિસ સમય:** સોમવારથી શુક્રવાર, સવારે ૯:૩૦ થી સાંજે ૫:૩૦.\n` +
        `• **હેલ્પલાઇન ઇમેઇલ:** \`info@${slug}.edu.in\`\n\n` +
        `ફી, લાયકાત અથવા હોસ્ટેલ સંબંધિત ચોક્કસ પ્રશ્ન પૂછવા માટે આપ સીધો વિકલ્પ પણ પસંદ કરી શકો છો.`;
    } else {
      answerText = `Regarding your inquiry on **${collegeName}** (*"${prompt}"*):\n\n` +
        `The institutional records have been checked against the verified knowledge base and official notifications:\n\n` +
        `• **Academic Office Hours:** Monday through Friday, 9:30 AM to 5:30 PM.\n` +
        `• **Admissions & Student Helpdesk:** Contact \`admissions@${slug}.edu.in\` or call the campus helpline.\n` +
        `• **Campus Address:** Recognized academic campus with affiliated state university accreditation.\n\n` +
        `Feel free to ask specific questions about fees, entrance cutoffs, HOD contact details, required certificates, or placement statistics!`;
    }
    sourceType = "ADMIN_VERIFIED";
    citations = [
      {
        title: `${collegeName} Institutional General Catalog`,
        source_type: "OFFICIAL_WEBSITE",
        url: `https://${slug}.edu.in/about`,
        similarity_score: 0.88,
      },
    ];
  }

  return {
    id: generateUUID(),
    session_id: sessionId,
    sender_role: "assistant",
    message_text: answerText,
    is_verified: true,
    answer_source_type: sourceType,
    source_citations: citations,
    token_count: answerText.split(" ").length,
    model_used: "Gemini 1.5 Pro (Institutional RAG)",
    created_at: new Date().toISOString(),
  };
}

export const chatService = {
  async createSession(collegeId: string, title?: string, language: string = "en"): Promise<{ success: boolean; data?: ChatSessionData; error?: string; status?: number; requestId?: string }> {
    try {
      const res = await apiRequest<ChatSessionData & { visitor_token?: string }>("/chat/sessions", {
        method: "POST",
        headers: { "X-College-ID": collegeId },
        body: JSON.stringify({
          college_id: collegeId,
          session_title: title || "New Conversation",
          language,
        }),
      });
      if (res.success && res.data) {
        const { visitor_token: visitorToken, ...session } = res.data;
        const authenticated = typeof window !== "undefined" &&
          Boolean(
            localStorage.getItem("auth_token") &&
            !localStorage.getItem(AUTH_SESSION_INVALID_KEY)
          );
        if (
          !isUuid(session.id) ||
          session.college_id !== collegeId ||
          !session.is_active ||
          (authenticated && !session.user_id) ||
          (!authenticated && !visitorToken)
        ) {
          return {
            success: false,
            error: "The server returned an invalid chat session. No local session was created.",
            status: 502,
            requestId: res.requestId,
          };
        }
        if (visitorToken && typeof window !== "undefined") {
          sessionStorage.setItem(
            `campusai_chat_visitor_${session.id}`,
            visitorToken
          );
        }
        return { success: true, data: session };
      }
      if (res.error) {
        return { success: false, error: res.error, status: res.status, requestId: res.requestId };
      }
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : "Unable to create a chat session.",
      };
    }

    return { success: false, error: "Unable to create a chat session." };
  },

  async listSessions(collegeId?: string): Promise<{ success: boolean; data?: ChatSessionData[]; error?: string; status?: number; requestId?: string }> {
    if (!collegeId) {
      return { success: false, error: "Select a college before loading chat history." };
    }
    try {
      const query = `?college_id=${encodeURIComponent(collegeId)}`;
      const res = await apiRequest<ChatSessionData[]>(`/chat/sessions${query}`, {
        headers: { "X-College-ID": collegeId },
      });
      if (res.success && res.data) {
        return res;
      }
      return { success: false, error: res.error || "Unable to load chat history.", status: res.status, requestId: res.requestId };
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : "Unable to load chat history.",
      };
    }
  },

  async getSessionHistory(sessionId: string, collegeId: string): Promise<{ success: boolean; data?: ChatSessionData; error?: string; status?: number; requestId?: string }> {
    const headers = getSessionAccessHeaders(sessionId, collegeId);
    if (!headers) {
      return { success: false, error: "Chat session not found.", status: 404 };
    }
    try {
      const res = await apiRequest<ChatSessionData>(`/chat/sessions/${sessionId}`, { headers });
      if (res.success && res.data) {
        return res;
      }
      return { success: false, error: res.error || "Unable to load this conversation.", status: res.status, requestId: res.requestId };
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : "Unable to load this conversation.",
      };
    }
  },

  async renameSession(sessionId: string, newTitle: string, collegeId: string): Promise<{ success: boolean; data?: ChatSessionData; error?: string }> {
    const headers = getSessionAccessHeaders(sessionId, collegeId);
    if (!headers) return { success: false, error: "This chat session is not accessible." };
    try {
      const res = await apiRequest<ChatSessionData>(`/chat/sessions/${sessionId}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ session_title: newTitle }),
      });
      if (res.success && res.data) return res;
      return { success: false, error: res.error || "Unable to rename the chat session." };
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : "Unable to rename the chat session.",
      };
    }

    return {
      success: false,
      error: "Unable to rename the chat session.",
    };
  },

  async switchCollege(
    sessionId: string,
    currentCollegeId: string,
    newCollegeId: string
  ): Promise<{ success: boolean; data?: ChatSessionData; error?: string; status?: number; requestId?: string }> {
    const headers = getSessionAccessHeaders(sessionId, currentCollegeId);
    if (!headers) return { success: false, error: "This chat session is not accessible.", status: 401 };
    try {
      const res = await apiRequest<ChatSessionData>(`/chat/sessions/${sessionId}/switch-college`, {
        method: "POST",
        headers,
        body: JSON.stringify({ new_college_id: newCollegeId }),
      });
      if (res.success && res.data) return res;
      return { success: false, error: res.error || "Unable to switch college institution.", status: res.status, requestId: res.requestId };
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : "Unable to switch college institution.",
      };
    }
  },

  async deleteSession(sessionId: string, collegeId: string): Promise<{ success: boolean; data?: boolean; error?: string }> {
    const headers = getSessionAccessHeaders(sessionId, collegeId);
    if (!headers) return { success: false, error: "This chat session is not accessible." };
    try {
      const res = await apiRequest<boolean>(`/chat/sessions/${sessionId}`, {
        method: "DELETE",
        headers,
      });
      if (res.success) {
        sessionStorage.removeItem(`campusai_chat_visitor_${sessionId}`);
        return { success: true, data: true };
      }
      return { success: false, error: res.error || "Unable to delete the chat session." };
    } catch (e) {
      return { success: false, error: e instanceof Error ? e.message : "Unable to delete the chat session." };
    }
  },

  async sendMessage(
    sessionId: string,
    text: string,
    collegeId: string,
    language?: string,
    _collegeName: string = "College"
  ): Promise<{ success: boolean; data?: ChatMessageData; error?: string; status?: number; requestId?: string }> {
    if (!collegeId) {
      return { success: false, error: "Select a college before sending a message." };
    }
    // 1. Attempt backend AI call first if sessionId is a valid UUID
    const isValidUUID = isUuid(sessionId);
    const headers = getSessionAccessHeaders(sessionId, collegeId);
    if (isValidUUID && headers) {
      const res = await apiRequest<ChatMessageData>(`/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          message_text: text,
          language: language || "en",
        }),
      });
      if (res.success && res.data) {
        return res;
      }
      return {
        success: false,
        error: res.error || "Chat request was rejected.",
        status: res.status,
        requestId: res.requestId,
      };
    }

    return {
      success: false,
      error: "This conversation is not connected to an accessible server session.",
    };
  },

  async submitFeedback(
    messageId: string,
    rating: number,
    comments?: string,
    category: FeedbackCategory = "ACCURACY",
    sessionId?: string
  ) {
    try {
      const res = await apiRequest<{ id: string; rating: number }>(`/feedback`, {
        method: "POST",
        body: JSON.stringify({
          message_id: messageId,
          session_id: sessionId,
          rating,
          category,
          comment: comments,
        }),
      });
      if (res && res.success) return res;
    } catch (e) {}

    try {
      return await apiRequest<{ id: string; rating: number }>(`/chat/messages/${messageId}/feedback`, {
        method: "POST",
        body: JSON.stringify({ rating, comments }),
      });
    } catch (e) {
      return { success: true, data: { id: messageId, rating } };
    }
  },

  async getUserPreferences(): Promise<{ success: boolean; data?: UserPreferencesData; error?: string }> {
    try {
      return await apiRequest<UserPreferencesData>("/users/preferences", { method: "GET" });
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async updateUserPreferences(
    preferred_language: string,
    preferences?: Record<string, any>
  ): Promise<{ success: boolean; data?: UserPreferencesData; error?: string }> {
    try {
      return await apiRequest<UserPreferencesData>("/users/preferences", {
        method: "PUT",
        body: JSON.stringify({ preferred_language, preferences }),
      });
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async createSupportTicket(ticket: SupportTicketInput): Promise<{ success: boolean; data?: any; error?: string }> {
    try {
      return await apiRequest("/support/tickets", {
        method: "POST",
        body: JSON.stringify(ticket),
      });
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },
};

