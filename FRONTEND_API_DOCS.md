# Rai Backend - Frontend & Mobile API Documentation

## Base Configuration
- **Base URL (Production):** `https://api.rai.imikemorgan.com` (or your configured VPS domain / server IP:port)
- **Content-Type:** `application/json`
- **Authentication Header:** All protected endpoints require a JWT Bearer token:
  ```http
  Authorization: Bearer <your_access_token>
  ```

---

## 🌟 Global Response Format
All API responses from Rai Backend are formatted using a standardized envelope:

### Successful Response:
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659848,
  "data": { ... } or [ ... ],
  "pagination": {          // Only present in paginated list responses
    "count": 10,
    "next": "https://.../?page=2",
    "previous": null
  },
  "errors": null
}
```

### Error Response:
```json
{
  "success": false,
  "code": 400,             // 400, 401, 403, 404, 500
  "message": "Validation error or error description",
  "timestamp": 1790659848,
  "data": null,
  "errors": {
    "field_name": ["Error detail message"]
  }
}
```

---

## 1. Comment & Concern API

Matches the mobile "Comment & Concern" and "Submit Comment & Concern" screens.

### 1.1 List All User Comments & Concerns
Fetches comments and concerns submitted by the authenticated user, newest first.

- **Method:** `GET`
- **Endpoint:** `/api/comments/` (alias: `/api/comment-concern/`)
- **Headers:** `Authorization: Bearer <token>`
- **Query Parameters (Optional):**
  - `page` (integer, default: 1)
  - `page_size` (integer, default: 20)

#### Real Response Example (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659848,
  "data": [
    {
      "id": "ce1ee158-b14d-4d1a-9a22-0e01e9347868",
      "ticket_code": "76XYJSDE",
      "message": "The parlay builder is awesome, please add risk warnings!",
      "status": "pending",
      "status_display": "Pending",
      "admin_reply": null,
      "created_at": "2026-09-29T05:30:48.335596Z",
      "formatted_date": "29 Sep 2026, 05:30 AM",
      "replied_at": null
    },
    {
      "id": "8a32d1f0-2d88-410a-8bf8-d6f731a54b38",
      "ticket_code": "5D5SG001",
      "message": "When will player prop stats be added?",
      "status": "replied",
      "status_display": "Replied",
      "admin_reply": "Player props are coming in version 2 next month!",
      "created_at": "2026-09-25T14:30:00Z",
      "formatted_date": "25 Sep 2026, 02:30 PM",
      "replied_at": "2026-09-25T16:10:00Z"
    }
  ],
  "pagination": {
    "count": 2,
    "next": null,
    "previous": null
  },
  "errors": null
}
```

> **UI Mapping Guide:**
> - `ticket_code`: 8-character unique ticket ID (e.g. `76XYJSDE`). Show this with the copy icon on the card.
> - `formatted_date`: Formatted string ready to display directly (e.g. `29 Sep 2026, 05:30 AM`).
> - `status_display`: `Pending` (display with orange/yellow badge) or `Replied` (display with green badge).
> - `admin_reply`: When status is `Replied`, contains the response from the admin.

---

### 1.2 Submit New Comment & Concern (Bottom Sheet)
Used by the "Submit Comment & Concern" bottom sheet modal.

- **Method:** `POST`
- **Endpoint:** `/api/comments/`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
```json
{
  "message": "The parlay builder is awesome, but I think a risk warning before placing high-leg parlays would really help users."
}
```

#### Real Response Example (`201 Created`):
```json
{
  "success": true,
  "code": 201,
  "message": "The parlay builder is awesome, but I think a risk warning before placing high-leg parlays would really help users.",
  "timestamp": 1790659848,
  "data": {
    "id": "ce1ee158-b14d-4d1a-9a22-0e01e9347868",
    "ticket_code": "76XYJSDE",
    "status": "pending",
    "status_display": "Pending",
    "admin_reply": null,
    "created_at": "2026-09-29T05:30:48.335596Z",
    "formatted_date": "29 Sep 2026, 05:30 AM",
    "replied_at": null
  },
  "errors": null
}
```

---

### 1.3 Get Single Comment & Concern Detail
- **Method:** `GET`
- **Endpoint:** `/api/comments/{id}/`
- **Headers:** `Authorization: Bearer <token>`

#### Response Example (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659848,
  "data": {
    "id": "ce1ee158-b14d-4d1a-9a22-0e01e9347868",
    "ticket_code": "76XYJSDE",
    "message": "The parlay builder is awesome, please add risk warnings!",
    "status": "replied",
    "status_display": "Replied",
    "admin_reply": "Thank you! We will add a risk disclaimer on high-leg parlays.",
    "created_at": "2026-09-29T05:30:48.335596Z",
    "formatted_date": "29 Sep 2026, 05:30 AM",
    "replied_at": "2026-09-29T06:00:00Z"
  },
  "errors": null
}
```

---

## 2. Notification System & Mobile Push (FCM) API

Used for mobile push notifications (Firebase Cloud Messaging), in-app alerts, bell icon badge count, and notification feed.

### 2.1 Register FCM Device Token (For Mobile Push Notifications)
Call this immediately after user logs in or whenever Firebase generates/refreshes the FCM registration token on the device (Android / iOS).

- **Method:** `POST`
- **Endpoint:** `/api/notifications/fcm-token/`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
```json
{
  "fcm_token": "eX_ample_fcm_token_generated_by_firebase_on_mobile_device_...",
  "device_type": "android"   // "android" or "ios" or "web"
}
```

#### Response (`200 OK` / `201 Created`):
```json
{
  "success": true,
  "code": 201,
  "message": "FCM device token registered successfully.",
  "timestamp": 1790659848,
  "data": {
    "device_id": "8b528a49-df63-4796-98dc-a760eb8c1566",
    "device_type": "android",
    "is_active": true
  },
  "errors": null
}
```

---

### 2.2 Remove FCM Device Token (Call On Logout)
Call this when the user logs out so they no longer receive push notifications on this device.

- **Method:** `POST` (or `DELETE`)
- **Endpoint:** `/api/notifications/fcm-token/remove/`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
```json
{
  "fcm_token": "eX_ample_fcm_token_generated_by_firebase_on_mobile_device_..."
}
```

#### Response (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "FCM device token removed/deactivated.",
  "timestamp": 1790659848,
  "data": {
    "success": true
  },
  "errors": null
}
```

---

### 2.3 Get Unread Notifications Count (For Bell Icon Badge)
Fast endpoint to get the unread notification count for badge rendering.

- **Method:** `GET`
- **Endpoint:** `/api/notifications/unread-count/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659848,
  "data": {
    "unread_count": 3
  },
  "errors": null
}
```

---

### 2.4 List User Notifications
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
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659848,
  "data": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Reply to your Comment & Concern",
      "message": "Admin replied to concern 76XYJSDE: Thank you! We will add a risk disclaimer on high-leg parlays...",
      "notification_type": "comment_reply",
      "reference_id": "76XYJSDE",
      "data": {
        "ticket_code": "76XYJSDE",
        "comment_id": "ce1ee158-b14d-4d1a-9a22-0e01e9347868"
      },
      "is_read": false,
      "created_at": "2026-09-29T06:00:00Z",
      "formatted_date": "29 Sep 2026, 06:00 AM"
    },
    {
      "id": "a1b2c3d4-e5f6-4a1b-8c2d-3e4f5a6b7c8d",
      "title": "Pick of the Day Available!",
      "message": "Today's high confidence pick is ready. Check it out now!",
      "notification_type": "betting",
      "reference_id": null,
      "data": {},
      "is_read": true,
      "created_at": "2026-09-29T04:00:00Z",
      "formatted_date": "29 Sep 2026, 04:00 AM"
    }
  ],
  "pagination": {
    "count": 2,
    "next": null,
    "previous": null
  },
  "errors": null
}
```

> **Notification Types:**
> - `comment_reply` : Admin replied to a comment & concern.
> - `support_reply` : Admin replied to a support ticket.
> - `betting` : Pick of the Day / betting picks alerts.
> - `community` : Community message or update.
> - `system` / `general` : App announcements and updates.

---

### 2.5 Mark Single Notification as Read
Triggered when user taps an unread notification card.

- **Method:** `POST`
- **Endpoint:** `/api/notifications/{id}/read/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "Marked as read",
  "timestamp": 1790659848,
  "data": {
    "is_read": true
  },
  "errors": null
}
```

---

### 2.6 Mark All Notifications as Read
Triggered when user taps "Mark all as read".

- **Method:** `POST`
- **Endpoint:** `/api/notifications/read-all/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "All 3 notifications marked as read.",
  "timestamp": 1790659848,
  "data": {
    "updated_count": 3
  },
  "errors": null
}
```

---

### 2.7 Clear / Delete All Read Notifications
- **Method:** `DELETE`
- **Endpoint:** `/api/notifications/clear-all/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "Cleared 5 read notifications.",
  "timestamp": 1790659848,
  "data": {
    "deleted_count": 5
  },
  "errors": null
}
```

---

### 2.8 Delete Single Notification
- **Method:** `DELETE`
- **Endpoint:** `/api/notifications/{id}/`
- **Headers:** `Authorization: Bearer <token>`

#### Response (`200 OK`):
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659848,
  "data": null,
  "errors": null
}
```

---

## 3. App Pages API (About us, Privacy Policy, Terms & Conditions)

These endpoints are **public** and do **NOT** require an Authorization token.

### 3.1 Get Page Content by Slug
- **Method:** `GET`
- **Endpoints:**
  - `GET /api/pages/about_us/` (About rai.)
  - `GET /api/pages/privacy_policy/` (Privacy Policy)
  - `GET /api/pages/terms_conditions/` (Terms & Conditions)

#### Real Response for `GET /api/pages/about_us/`:
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659752,
  "data": {
    "slug": "about_us",
    "title": "About rai.",
    "content": "rai. is an AI-powered sports assistant built to make sports betting smarter, clearer, and less stressful.\n\nWe combine data, analytics, and artificial intelligence with a friendly tone and light humor to help users:\n• Save time researching games\n• Make confident decisions\n• Avoid emotional betting\n• Build smarter parlays\n• Our mission is simple:\n\nHelp users bet smarter — not harder.",
    "updated_at": "2026-09-29T05:27:04.485285Z"
  },
  "errors": null
}
```

#### Real Response for `GET /api/pages/privacy_policy/`:
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659753,
  "data": {
    "slug": "privacy_policy",
    "title": "Privacy Policy",
    "content": "Last updated: November 13, 2025\n\nAt rai, your privacy matters. We are committed to protecting your personal information and being transparent about how data is used.\n\nWhat We Collect\n• Account information (name, email, username)\n• Usage data to improve AI predictions and app performance\n• Optional profile details such as bio and profile photo\n\nHow We Use Your Data\n• To provide personalized picks and insights\n• To improve AI accuracy and user experience\n• To detect risky or emotional betting behavior\n• To manage subscriptions and account access\n\nWe never sell your personal data. All information is stored securely and used only to enhance your experience with rai.",
    "updated_at": "2026-09-29T05:27:04.490520Z"
  },
  "errors": null
}
```

#### Real Response for `GET /api/pages/terms_conditions/`:
```json
{
  "success": true,
  "code": 200,
  "message": "Request successful",
  "timestamp": 1790659753,
  "data": {
    "slug": "terms_conditions",
    "title": "Terms & Conditions",
    "content": "Effective Date: 1st December 2025\n\nBy using rai, you agree to the following terms:\n• rai provides AI-generated insights for informational purposes only\n• All picks are suggestions, not guarantees\n• Users must be 18 years or older\n• You are responsible for your own betting decisions\n• rai is not affiliated with any sportsbook and does not place bets on your behalf\n\nMisuse of the app, abuse of features, or violation of rules may result in account suspension.",
    "updated_at": "2026-09-29T05:27:04.493565Z"
  },
  "errors": null
}
```

---

### 3.2 List All Pages
- **Method:** `GET`
- **Endpoint:** `/api/pages/`

Returns an array containing all three pages (`about_us`, `privacy_policy`, `terms_conditions`).
