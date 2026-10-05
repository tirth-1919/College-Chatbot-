export default async function run(page, ui) {
  const requests = [];
  const responses = [];
  page.on('request', request => { if (request.url().includes('/api/')) requests.push({ method: request.method(), url: request.url(), postData: request.postData() }); });
  page.on('response', async response => { if (response.url().includes('/api/')) { let body = ''; try { body = await response.text(); } catch { } responses.push({ url: response.url(), status: response.status(), body: body.slice(0, 1000) }); } });
  await page.getByPlaceholder('admin@yourcollege.edu').fill('4@gmail.com');
  await page.locator('input[type="password"]').fill('1');
  await page.getByRole('button', { name: 'Sign In to Admin Panel' }).click();
  await page.waitForTimeout(1200);
  const login = await ui.snapshot({ full: true });
  const nav = await ui.snapshot();
  const users = nav.match(/@(e\d+) button "All Users"/)?.[1];
  if (!users) return { login, nav, requests, responses };
  await ui.click('@' + users);
  await page.waitForTimeout(1200);
  return { after: await ui.snapshot({ full: true }), body: (await page.locator('body').innerText()).slice(0, 3000), requests, responses };
}