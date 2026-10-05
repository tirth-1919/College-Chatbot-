export function getProvenanceBadge(message) {
  const provenance = message?.provenance || message;
  const blockProvenance = message?.blocks?.find(block => block?.type === 'provenance');
  const source = { ...blockProvenance, ...provenance };
  const status = source.answer_status || source.source_type || source.answer_source || message?.answer_source;
  const verified = source.verified === true;
  const collegeName = source.source_context?.active_college_name || source.active_college_name;

  if (status === 'NO_VERIFIED_INFORMATION') {
    return { kind: 'gemini', label: '🤖 Gemini Answer — Not Verified' };
  }
  if (status === 'GEMINI_UNVERIFIED') {
    return { kind: 'gemini', label: '🤖 Gemini Answer — Not Verified' };
  }
  if (status === 'OFFICIAL_WEBSITE' && verified) {
    return { kind: 'official', label: collegeName ? `🌐 Official Website — ${collegeName}` : '🌐 Official Website' };
  }
  if (status === 'ADMIN_VERIFIED' && verified) {
    return { kind: 'admin', label: collegeName ? `🗄️ ${collegeName} Database` : '🗄️ College Database' };
  }
  return null;
}
