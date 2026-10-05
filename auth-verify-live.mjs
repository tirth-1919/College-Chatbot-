export default async function run(page, ui) {
  const email = `verify-${Date.now()}@e2e.localtest`;
  const password = 'E2E-Student-Password-2026!';
  await page.evaluate(() => [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Sign In')?.click());
  await page.waitForTimeout(200);
  await page.getByPlaceholder('name@example.com').fill('1@gmail.com');
  await page.locator('input[type="password"]').fill('1');
  await page.getByRole('button', { name: 'Sign In', exact: true }).click();
  await page.waitForTimeout(1500);
  const responses = [];
  const listener = async response => {
    if (response.url().includes('/api/v1/chat')) {
      try { responses.push({ url: response.url(), status: response.status(), body: await response.text() }); } catch (e) { responses.push({ url: response.url(), status: response.status(), error: String(e) }); }
    }
  };
  page.on('response', listener);
  const box = page.getByRole('textbox', { name: 'Ask anything about your college...' });
  await box.fill('What documents are required for the BCA program at Ahmedabad Institute of Technology?');
  await page.getByRole('button', { name: 'Send query' }).click();
  await page.waitForTimeout(7000);
  page.off('response', listener);
  const bodyText = await page.locator('body').innerText();
  const resources = await page.evaluate(() => performance.getEntriesByType('resource').map(e => e.name).filter(n => n.includes('.js')));
  const bundleChecks = [];
  for (const url of [...new Set(resources)]) {
    try { const text = await (await fetch(url)).text(); bundleChecks.push({ url, hasNoVerified: text.includes('NO_VERIFIED_INFORMATION'), hasWarning: text.includes('Gemini-generated') }); } catch (e) { }
  }
  return { email, bodyText, responses, bundleChecks, snapshot: await ui.snapshot({ full: true }), localStorage: await page.evaluate(() => ({ ...localStorage })) };
}
