# NepalTrail — Smart Tourism Platform

## Project Structure

```
nepaltrail/
├── server.py          ← Flask backend (all API routes)
├── nepaltrail.db      ← SQLite database (auto-created on first run)
├── requirements.txt
├── README.md
└── public/
    └── index.html     ← React frontend (served by Flask)
```

## Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the server
```bash
python server.py
```

### 3. Open your browser
```
http://localhost:5000
```

---

## Default Demo Account
- **Email:** maya@nepaltrail.com  
- **Password:** demo123

Or register a new account on the login screen.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| GET  | `/api/user/<id>` | Get user profile |
| PUT  | `/api/user/<id>/credits` | Update user credits |
| GET  | `/api/routes` | List trekking routes |
| GET  | `/api/accommodations` | List accommodations |
| GET  | `/api/guides` | List guides |
| GET  | `/api/transport` | List transport options |
| GET  | `/api/bookings?user_id=` | Get user bookings |
| POST | `/api/bookings` | Create a booking |
| GET  | `/api/feedbacks` | Get all feedbacks |
| POST | `/api/feedbacks` | Submit trail feedback |
| GET  | `/api/checkins?user_id=` | Get user check-ins |
| POST | `/api/checkins` | QR check-in at checkpoint |
| POST | `/api/sos` | Submit SOS alert |
| GET  | `/api/sos?user_id=` | Get SOS history |
| GET  | `/api/health` | Health check |

---

## Database Schema (SQLite)

- **users** — id, name, email, password (SHA-256), avatar, rank, credits, created_at
- **bookings** — id, user_id, item_name, item_type, price, emoji, booking_ref, date, status
- **feedbacks** — id, user_id, user_name, location, rating, condition, comment, date
- **checkins** — id, user_id, checkpoint_id, checkpoint_name, altitude, credits_earned, timestamp
- **sos_alerts** — id, user_id, user_name, sos_type, symptoms, latitude, longitude, status, timestamp

---

## What the Backend Does

1. **Auth** — Register/login with SHA-256 hashed passwords; sessions managed client-side via user ID in React state
2. **Bookings** — All transport, accommodation and guide bookings saved to DB with unique reference codes
3. **Feedbacks** — Trail feedback persisted and loaded from DB for community sharing
4. **QR Check-ins** — Validates uniqueness per user per checkpoint; credits are credited in DB
5. **SOS Alerts** — Emergency alerts stored with GPS coordinates and symptoms
6. **Credits** — Maintained in DB; incremented on each valid QR check-in
