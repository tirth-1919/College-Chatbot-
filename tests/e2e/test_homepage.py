from playwright.sync_api import Page, expect


def test_college_chatbot_homepage(page: Page):
    page.goto("http://127.0.0.1:5174")

    expect(page).to_have_title("AI FAQ College Chat Bot")

    expect(
        page.get_by_role("heading", name="AI FAQ College Chat Bot")
    ).to_be_visible()

    expect(
        page.get_by_role("main").get_by_text(
            "Ask anything about your college", exact=True
        )
    ).to_be_visible()

    expect(
        page.get_by_role("button", name="Start New Chat")
    ).to_be_visible()

def test_start_new_chat_shows_chat_input(page: Page):
    page.goto("http://127.0.0.1:5174")

    page.get_by_role("button", name="Start New Chat").click()

    chat_input = page.locator(
        'textarea[placeholder="Ask anything about your college..."]'
    )

    expect(chat_input).to_be_visible()

def test_chat_input_enables_send_button(page: Page):
    page.goto("http://127.0.0.1:5174")

    page.get_by_role("button", name="Start New Chat").click()

    chat_input = page.locator(
        'textarea[placeholder="Ask anything about your college..."]'
    )

    send_button = page.get_by_role("button", name="Send query")

    expect(send_button).to_be_disabled()

    chat_input.fill("What courses are offered by Ahmedabad Institute of Technology?")

    expect(send_button).to_be_enabled()


def test_chat_submission_shows_assistant_response(page: Page):
    page.goto("http://127.0.0.1:5174")

    page.get_by_role("button", name="Start New Chat").click()

    chat_input = page.locator(
        'textarea[placeholder="Ask anything about your college..."]'
    )

    chat_input.fill(
        "What courses are offered by Ahmedabad Institute of Technology?"
    )

    page.get_by_role("button", name="Send query").click()

    # Wait for the assistant response to appear.
    expect(
        page.get_by_text(
            "What courses are offered by Ahmedabad Institute of Technology?",
            exact=True,
        )
    ).to_be_visible()

    expect(
        page.locator("main").get_by_text(
            "What courses are offered by Ahmedabad Institute of Technology?",
            exact=True,
        )
    ).to_be_visible()