export default async function run(page, ui) {
  const box = page.getByRole('textbox', { name: 'Ask anything about your college...' });
  await box.fill('What documents are required for the BCA program at Ahmedabad Institute of Technology?');
  await page.getByRole('button', { name: 'Send query' }).click();
  await page.waitForTimeout(1200);
  return {
    snapshot: await ui.snapshot({ full: true }),
    bodyText: await page.locator('body').innerText(),
    localStorage: await page.evaluate(() => ({ ...localStorage })),
    sessionStorage: await page.evaluate(() => ({ ...sessionStorage })),
  };
}
