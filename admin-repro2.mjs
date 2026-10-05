export default async function run(page, ui) {
  const requests = [], responses = [];
  page.on('request', r => { if (r.url().includes('/api/')) requests.push({ method: r.method(), url: r.url() }); });
  page.on('response', async r => { if (r.url().includes('/api/')) { let body = ''; try { body = await r.text(); } catch { } responses.push({ url: r.url(), status: r.status(), body: body.slice(0, 500) }); } });
  await page.getByPlaceholder('admin@yourcollege.edu').fill('admin@aitindia.in');
  await page.locator('input[type="password"]').fill('1');
  await page.getByRole('button', { name: 'Sign In to Admin Panel' }).click();
  await page.waitForTimeout(1000);
  const nav = await ui.snapshot();
  const users = nav.match(/@(e\d+) button "All Users"/)?.[1];
  if (!users) return { page: await ui.snapshot({ full: true }), requests, responses };
  await ui.click('@' + users); await page.waitForTimeout(1000);
  return { page: await ui.snapshot({ full: true }), body: (await page.locator('body').innerText()).slice(-2500), requests, responses };
}