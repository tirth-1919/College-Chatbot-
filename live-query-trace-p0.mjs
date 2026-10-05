export default async function run(page, ui) {
  await page.getByRole('button', { name: 'Sign In / Sign Up' }).click();
  await page.waitForTimeout(300);
  await page.getByPlaceholder('name@example.com').fill('1@gmail.com');
  await page.locator('input[type="password"]').fill('1');
  await page.getByRole('button', { name: 'Sign In', exact: true }).click();
  await page.waitForTimeout(1500);
  const responses = [];
  const listener = async response => {
    if (response.url().includes('/api/v1/chat/stream')) {
      try { responses.push({ url: response.url(), status: response.status(), body: await response.text() }); } catch (e) { responses.push({ url: response.url(), status: response.status(), error: String(e) }); }
    }
  };
  page.on('response', listener);
  const box = page.getByRole('textbox', { name: 'Ask anything about your college...' });
  await box.fill('What documents are required for BCA admission?');
  await page.getByRole('button', { name: 'Send query' }).click();
  await page.waitForTimeout(8000);
  page.off('response', listener);
  return { bodyText: await page.locator('body').innerText(), responses, snapshot: await ui.snapshot({ full: true }) };
}
