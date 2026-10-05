export default async function run(page, ui) {
  const before = await ui.snapshot();
  const ref = before.match(/@(e\d+) button "Start New Chat"/)?.[1];
  if (!ref) return { clicked: false, error: 'Start New Chat button not found', before };
  await ui.click(`@${ref}`);
  await page.waitForTimeout(100);
  return {
    clicked: true,
    focusedComposer: await page.evaluate(() => document.activeElement?.classList.contains('composer-textarea')),
    currentId: await page.evaluate(() => document.querySelector('.chat-topbar')?.textContent?.includes('AI FAQ College Chat Bot'))
  };
}
