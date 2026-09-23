import { test, expect } from '@playwright/test';

test.describe('College Registration Navigation & Role Separation', () => {
  test('test_clicking_register_college_opens_registration_form', async ({ page }) => {
    // 1. Visit User Portal
    await page.goto('/');

    // 2. Open login modal
    const signInBtn = page.getByRole('button', { name: /sign in/i }).first();
    await signInBtn.click();

    // 3. Find and click "Register Your College" link
    const registerLink = page.getByRole('link', { name: /register your college/i });
    await expect(registerLink).toBeVisible();
    await registerLink.click();

    // 4. Verify URL has navigated to /register-college
    await expect(page).toHaveURL(/\/register-college$/);

    // 5. Verify the College Registration Form is visible
    await expect(page.getByRole('heading', { name: 'Register Your College' })).toBeVisible();
    await expect(page.getByPlaceholder(/ahmedabad institute of technology/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Submit Registration' })).toBeVisible();

    // 6. Verify Admin Dashboard is NOT visible
    await expect(page.getByText(/Control Center|Platform Super Admin Dashboard/i)).toHaveCount(0);
    await expect(page.locator('.admin-layout, .admin-sidebar')).toHaveCount(0);
  });

  test('test_college_registration_submission_creates_pending_request', async ({ page }) => {
    // 1. Directly visit /register-college
    await page.goto('/register-college');

    // 2. Verify form is rendered
    await expect(page.getByRole('heading', { name: 'Register Your College' })).toBeVisible();

    const uniqueId = Math.floor(Math.random() * 90000) + 10000;
    // 3. Fill required fields
    await page.locator('input[name="college_name"]').fill(`Playwright Test College ${uniqueId}`);
    await page.locator('input[name="college_code"]').fill(`PTC${uniqueId % 1000}`);
    await page.locator('input[name="official_website"]').fill(`https://testcollege-${uniqueId}.org`);
    await page.locator('input[name="official_email"]').fill(`contact@testcollege-${uniqueId}.org`);
    await page.locator('input[name="contact_person"]').fill('Principal Tester');
    await page.locator('input[name="contact_email"]').fill(`principal@testcollege-${uniqueId}.org`);
    await page.locator('input[name="contact_phone"]').fill('9876543210');
    await page.locator('input[name="address"]').fill('123 Testing Road');
    await page.locator('input[name="city"]').fill('Ahmedabad');
    await page.locator('input[name="state"]').fill('Gujarat');

    // 4. Submit registration
    await page.getByRole('button', { name: 'Submit Registration' }).click();

    // 5. Verify confirmation screen
    await expect(page.getByText('Registration Submitted Successfully')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/COL-2026-/)).toBeVisible();
    await expect(page.getByText(/PENDING/i).first()).toBeVisible();

    // 6. Verify user is NOT redirected to /admin/dashboard
    expect(page.url()).not.toContain('/admin/dashboard');
  });

  test('test_college_admin_does_not_see_registration_creation', async ({ page }) => {
    // Visit Admin login page on port 8001
    await page.goto('http://127.0.0.1:8001/');

    // Ensure "Register Your College" promotion does NOT exist on Admin Login
    await expect(page.getByRole('button', { name: /register your college/i })).toHaveCount(0);
    await expect(page.getByRole('link', { name: /register your college/i })).toHaveCount(0);
  });
});
