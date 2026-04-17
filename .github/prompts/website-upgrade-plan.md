### 🎯 Objective
Upgrade the `wizard_backend` FastAPI website to include a modern landing page, a global navigation menu, and a public feedback system with upvote/downvote functionality. 

### 🛠️ Context
- The backend is built with **FastAPI** and uses **Jinja2** for templates.
- The web files are located in `wizard_backend/` (specifically `main.py`, `database.py`, and `templates/`).

#### Step 1: Establish a Shared Base Template
1. **Create `wizard_backend/templates/base.html`:**
   - Set up a standard HTML5 boilerplate.
   - Include a modern CSS framework (e.g., Tailwind CSS via CDN or Bootstrap) to ensure the site looks sleek and intriguing.
   - Create a **Global Navigation Menu** with links to:
     - Home (`/`)
     - Global Leaderboard (`/leaderboard`)
     - Feedback (`/feedback`)
2. **Refactor `wizard_backend/templates/leaderboard.html`:**
   - Modify the file to extend `base.html` using Jinja2 inheritance (`{% extends "base.html" %}`).
   - Wrap the existing leaderboard content in a `{% block content %}` tag.

#### Step 2: Build the Intriguing Landing Page (Home)
1. **Route Update in `wizard_backend/main.py`:**
   - Create or modify the root endpoint `GET /` to return a `TemplateResponse` for `index.html`.
2. **Create `wizard_backend/templates/index.html`:**
   - Extend `base.html`.
   - **Hero Section:** Add an exciting, intriguing headline and a brief description summarizing what the app is about.
   - **Call-to-Action (CTA) Buttons:**
     - Add a "Download for Windows (.exe)" button. Set the `href` to point to the GitHub releases page or the static executable path.
     - Add "Download on the App Store" and "Get it on Google Play" buttons. Leave their `href` attributes blank (`#`) for now, but style them prominently.
     - Add a link/icon to the project's GitHub repository.

#### Step 3: Implement the Database Schema for Feedback
1. **Update `wizard_backend/database.py`:**
   - Create a new data model/table named `Feedback`.
   - Fields should include:
     - `id` (Integer, Primary Key)
     - `message` (String/Text)
     - `upvotes` (Integer, default 0)
     - `downvotes` (Integer, default 0)
     - `created_at` (DateTime)
   - Ensure the database initialization script creates this table if it doesn't already exist.

#### Step 4: Build the Feedback API & Endpoints
1. **Update `wizard_backend/main.py`:**
   - **`GET /feedback`**: Fetch all feedback records from the database, sorted dynamically (e.g., by highest net votes `upvotes - downvotes` and then by date), and render `feedback.html`.
   - **`POST /api/feedback`**: Accept form data or JSON containing a new message, validate it, insert it into the database, and return a success response or redirect.
   - **`POST /api/feedback/{id}/vote`**: Accept a payload specifying the vote type (`up` or `down`). Update the respective counter in the `Feedback` table.

#### Step 5: Implement the Feedback UI
1. **Create `wizard_backend/templates/feedback.html`:**
   - Extend `base.html`.
   - **GitHub Link:** Prominently display a message like: *"Found a bug or want to contribute? [Create an issue directly on GitHub](#)".*
   - **Submission Form:** Create a text area and a submit button for users to post new public messages, ideas, or feature requests. 
   - **Message Feed:** Iterate over the feedback records passed from the backend (`{% for item in feedbacks %}`). Provide the text, creation date, and vote counts.
   - **Voting Interactivity:** Add Upvote and Downvote buttons next to each message. Bind them to JavaScript functions (e.g., using `fetch()`) that call the `/api/feedback/{id}/vote` endpoint and increment the local UI counters upon success without requiring a full page reload.

#### Step 6: Polish and Verification
- Ensure all forms have basic validation (preventing empty message submissions).
- Make sure the UI is mobile-friendly.
- Verify that navigating between Home, Leaderboard, and Feedback works seamlessly via the new navigation bar.