# Rai Backend - Frontend API Documentation

## Base Information
- **Base URL (Production):** `https://api.rai.imikemorgan.com` (or your configured domain/IP)
- **Authentication:** All protected endpoints require a JWT Bearer token in the request header:
  ```http
  Authorization: Bearer <your_access_token>
  ```
- **Content-Type:** `application/json`

---

## 1. Comment & Concern API

Used for user feedback, concerns, and suggestions matching the mobile UI screens.

### 1.1 List All User Comments & Concerns
Fetches all comments/concerns submitted by the authenticated user, ordered from newest to oldest.

- **Method:** `GET`
- **Endpoint:** `/api/comments/` (or `/api/comment-concern/`)
- **Headers:** `Authorization: Bearer <token>`
- **Query Parameters (Optional):**
  - `page` (integer, default: 1)
  - `page_size` (integer, default: 20, max: 100)

#### Response (`200 OK`):
```json
{
  "count": 4,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "ticket_code": "5D5SG001",
      "message": "The parlay builder is awesome, but I think a risk warning before placing high-leg parlays would really help users.",
      "status": "pending",
      "status_display": "Pending",
      "admin_reply": null,
      "created_at": "2025-08-25T20:54:10Z",
      "formatted_date": "25 Aug 2025, 08:54 PM",
      "replied_at": null
    },
    {
      "id": "e4a29a43-6d08-410a-8bf8-d6f731a54b38",
      "ticket_code": "9K2LX442",
      "message": "Would love to see player prop statistics included in the next update!",
      "status": "replied",
      "status_display": "Replied",
      "admin_reply": "Thanks for your feedback! Player props are currently in development for version 2.",
      "created_at": "2025-08-25T14:30:00Z",
      "formatted_date": "25 Aug 2025, 02:30 PM",
      "replied_at": "2025-08-25T16:10:00Z"
    }
  ]
}
```

> **UI Mapping Note:**
> - `ticket_code`: Show this as the ticket ID with the copy icon (e.g. `5D5SG001`).
> - `formatted_date`: Directly formatted as `25 Aug 2025, 08:54 PM` ready for display.
> - `status_display`: `Pending` (display with orange/yellow badge) or `Replied` (display with green badge).

---

### 1.2 Submit New Comment & Concern
Opens from the bottom sheet modal ("Submit Comment & Concern"). Only the `message` field is required.

- **Method:** `POST`
- **Endpoint:** `/api/comments/`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
```json
{
  "message": "The parlay builder is awesome, but I think a risk warning before placing high-leg parlays would really help users."
}
```

#### Response (`201 Created`):
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "ticket_code": "5D5SG001",
  "message": "The parlay builder is awesome, but I think a risk warning before placing high-leg parlays would really help users.",
  "status": "pending",
  "status_display": "Pending",
  "admin_reply": null,
  "created_at": "2025-08-25T20:54:10Z",
  "formatted_date": "25 Aug 2025, 08:54 PM",
  "replied_at": null
}
```

---

### 1.3 Get Single Comment & Concern Detail
- **Method:** `GET`
- **Endpoint:** `/api/comments/{id}/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "ticket_code": "5D5SG001",
  "message": "The parlay builder is awesome, but I think a risk warning before placing high-leg parlays would really help users.",
  "status": "replied",
  "status_display": "Replied",
  "admin_reply": "Thank you! We will add a risk disclaimer on high-leg parlays.",
  "created_at": "2025-08-25T20:54:10Z",
  "formatted_date": "25 Aug 2025, 08:54 PM",
  "replied_at": "2025-08-25T22:00:00Z"
}
```

---

## 2. Notification System API

Used for in-app user alerts, bell icon badge count, and notification feed.

### 2.1 Get Unread Notifications Count (For Bell Icon Badge)
Fast endpoint to check how many unread notifications exist.

- **Method:** `GET`
- **Endpoint:** `/api/notifications/unread-count/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "unread_count": 3
}
```

---

### 2.2 List User Notifications
Fetches all user notifications ordered by newest first.

- **Method:** `GET`
- **Endpoint:** `/api/notifications/`
- **Headers:** `Authorization: Bearer <token>`
- **Query Parameters (Optional):**
  - `page` (integer, default: 1)
  - `page_size` (integer, default: 20)

#### Response (`200 OK`):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Reply to your Comment & Concern",
      "message": "Admin replied to concern 5D5SG001: Thank you! We will add a risk disclaimer on high-leg parlays...",
      "notification_type": "comment_reply",
      "reference_id": "5D5SG001",
      "data": {
        "ticket_code": "5D5SG001",
        "comment_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
      },
      "is_read": false,
      "created_at": "2025-08-25T22:00:00Z",
      "formatted_date": "25 Aug 2025, 10:00 PM"
    },
    {
      "id": "a1b2c3d4-e5f6-4a1b-8c2d-3e4f5a6b7c8d",
      "title": "Pick of the Day Available!",
      "message": "Today's high confidence pick is ready. Check it out now!",
      "notification_type": "betting",
      "reference_id": null,
      "data": {},
      "is_read": true,
      "created_at": "2025-08-25T10:00:00Z",
      "formatted_date": "25 Aug 2025, 10:00 AM"
    }
  ]
}
```

> **Notification Types:**
> - `comment_reply` : Reply received for a comment & concern.
> - `support_reply` : Reply received for a support ticket.
> - `betting` : Pick of the day / new betting picks alert.
> - `community` : Community announcement or message.
> - `system` / `general` : App updates or general announcements.

---

### 2.3 Mark Single Notification as Read
Triggered when the user taps on an unread notification.

- **Method:** `POST`
- **Endpoint:** `/api/notifications/{id}/read/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "message": "Marked as read",
  "is_read": true
}
```

---

### 2.4 Mark All Notifications as Read
Triggered when the user taps "Mark all as read".

- **Method:** `POST`
- **Endpoint:** `/api/notifications/read-all/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "message": "All 3 notifications marked as read.",
  "updated_count": 3
}
```

---

### 2.5 Clear / Delete All Read Notifications
- **Method:** `DELETE`
- **Endpoint:** `/api/notifications/clear-all/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "message": "Cleared 5 read notifications.",
  "deleted_count": 5
}
```

---

### 2.6 Delete Single Notification
- **Method:** `DELETE`
- **Endpoint:** `/api/notifications/{id}/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`204 No Content`)

---

## 3. App Pages API (About us, Privacy Policy, Terms & Conditions)

These endpoints are **public** and do **NOT** require an Authorization token.

### 3.1 Get Specific Page Content by Slug
- **Method:** `GET`
- **Endpoints:**
  - `GET /api/pages/about_us/` (About rai.)
  - `GET /api/pages/privacy_policy/` (Privacy Policy)
  - `GET /api/pages/terms_conditions/` (Terms & Conditions)

#### Example Response for `GET /api/pages/about_us/`:
```json
{
  "id": "527a974b-e3a1-432d-8692-a1f0a0684f50",
  "slug": "about_us",
  "title": "About rai.",
  "content": "rai. is an AI-powered sports assistant built to make sports betting smarter, clearer, and less stressful.\n\nWe combine data, analytics, and artificial intelligence with a friendly tone and light humor to help users:\n• Save time researching games\n• Make confident decisions\n• Avoid emotional betting\n• Build smarter parlays\n• Our mission is simple:\n\nHelp users bet smarter — not harder.",
  "created_at": "2026-09-29T10:40:00Z",
  "updated_at": "2026-09-29T10:40:00Z"
}
```

#### Example Response for `GET /api/pages/privacy_policy/`:
```json
{
  "id": "673f4d02-3c8e-4a64-96cf-dfdb90c29f4b",
  "slug": "privacy_policy",
  "title": "Privacy Policy",
  "content": "Last updated: November 13, 2025\n\nAt rai, your privacy matters. We are committed to protecting your personal information and being transparent about how data is used.\n\nWhat We Collect\n• Account information (name, email, username)\n• Usage data to improve AI predictions and app performance\n• Optional profile details such as bio and profile photo\n\nHow We Use Your Data\n• To provide personalized picks and insights\n• To improve AI accuracy and user experience\n• To detect risky or emotional betting behavior\n• To manage subscriptions and account access\n\nWe never sell your personal data. All information is stored securely and used only to enhance your experience with rai.",
  "created_at": "2026-09-29T10:40:00Z",
  "updated_at": "2026-09-29T10:40:00Z"
}
```

#### Example Response for `GET /api/pages/terms_conditions/`:
```json
{
  "id": "9bc323fb-0fae-4fe1-ba5f-b5dc732551ec",
  "slug": "terms_conditions",
  "title": "Terms & Conditions",
  "content": "Effective Date: 1st December 2025\n\nBy using rai, you agree to the following terms:\n• rai provides AI-generated insights for informational purposes only\n• All picks are suggestions, not guarantees\n• Users must be 18 years or older\n• You are responsible for your own betting decisions\n• rai is not affiliated with any sportsbook and does not place bets on your behalf\n\nMisuse of the app, abuse of features, or violation of rules may result in account suspension.",
  "created_at": "2026-09-29T10:40:00Z",
  "updated_at": "2026-09-29T10:40:00Z"
}
```

---

### 3.2 List All Pages
- **Method:** `GET`
- **Endpoint:** `/api/pages/`

Returns an array of all active pages (`about_us`, `privacy_policy`, `terms_conditions`).
