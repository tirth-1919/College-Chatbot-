import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { getProvenanceBadge } from './provenanceBadge.js';

describe('provenance badge rendering', () => {
  it('does not use a Gemini or verified badge for NO_VERIFIED_INFORMATION on the message rendering path', () => {
    const badge = getProvenanceBadge({
      answer_status: 'NO_VERIFIED_INFORMATION',
      source_type: 'NO_VERIFIED_INFORMATION',
      grounding_status: 'unverified',
      verification_status: 'unverified',
      provenance: {
        answer_status: 'NO_VERIFIED_INFORMATION',
        source_type: 'NO_VERIFIED_INFORMATION',
        verified: false,
      },
      blocks: [{
        type: 'provenance',
        answer_status: 'NO_VERIFIED_INFORMATION',
        source_type: 'NO_VERIFIED_INFORMATION',
        verified: false,
      }],
    });

    assert.deepEqual(badge, { kind: 'gemini', label: '🤖 Gemini Answer — Not Verified' });
  });

  it('preserves the exact Gemini warning for GEMINI_UNVERIFIED on the message rendering path', () => {
    assert.deepEqual(
      getProvenanceBadge({
        grounding_status: 'general_ai',
        provenance: { answer_status: 'GEMINI_UNVERIFIED', verified: false },
        blocks: [{ type: 'provenance', answer_status: 'GEMINI_UNVERIFIED', verified: false }],
      }),
      { kind: 'gemini', label: '🤖 Gemini Answer — Not Verified' },
    );
  });

  it('preserves verified badges only for verified official/admin sources', () => {
    assert.deepEqual(
      getProvenanceBadge({ answer_status: 'OFFICIAL_WEBSITE', verified: true }),
      { kind: 'official', label: '🌐 Official Website' },
    );
    assert.deepEqual(
      getProvenanceBadge({ answer_status: 'ADMIN_VERIFIED', verified: true }),
      { kind: 'admin', label: '🗄️ College Database' },
    );
    assert.equal(getProvenanceBadge({ answer_status: 'OFFICIAL_WEBSITE', verified: false }), null);
    assert.equal(getProvenanceBadge({ answer_status: 'ADMIN_VERIFIED', verified: false }), null);
  });
});
