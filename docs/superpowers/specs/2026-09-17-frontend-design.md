# Frontend Design Spec — Finwise Expense Tracker

## Overview

AI-powered expense tracker with a conversational agent as the primary interface. The frontend is a Next.js app with Tailwind CSS, consuming a FastAPI backend with SSE streaming for chat and REST endpoints for direct data access.

## Architecture

```
memory-agent/
├── app/                  # FastAPI backend (existing)
├── frontend/             # Next.js frontend (new)
│   ├── src/
│   │   ├── app/          # Next.js app router pages
│   │   ├── components/   # UI components
│   │   ├── lib/          # API client, utils
│   │   └── types/        # TypeScript types
│   ├── public/
│   └── package.json
└── docs/
```

### Backend additions needed

- `POST /api/chat/stream` — SSE streaming endpoint for agent chat
- `GET /api/expenses` — List expenses with filters
- `GET /api/expenses/:id` — Single expense detail
- `PUT /api/expenses/:id` — Update expense
- `DELETE /api/expenses/:id` — Delete expense
- `GET /api/stats` — Expense aggregates for insights

### API client

- `frontend/src/lib/api.ts` — typed fetch wrapper
- `frontend/src/lib/chat.ts` — SSE streaming handler

## Design Tokens

### Color

| Token | Hex | Role |
|-------|-----|------|
| `--bg` | `#FAFAFA` | Page background |
| `--surface` | `#FFFFFF` | Cards, sidebar, inputs |
| `--border` | `#E5E5E5` | Dividers, subtle edges |
| `--text` | `#171717` | Primary text |
| `--text-muted` | `#737373` | Secondary text, labels |
| `--accent` | `#171717` | Primary actions, active nav, agent avatar |
| `--user-bubble` | `#F5F5F5` | User message background |

No gradients. No accent colors. Personality from restraint.

### Typography

- **Font:** Inter (via `next/font/google`)
- **Scale:**
  - Page title: 18px / weight 600
  - Section heading: 14px / weight 600
  - Body: 14px / weight 400
  - Small/meta: 12px / weight 400
  - Chat input: 14px / weight 400
- **Line height:** 1.5 body, 1.4 headings
- **Case:** Sentence case everywhere. No ALL-CAPS labels.

## Layout

### Desktop (≥1024px)

- Fixed left sidebar: 240px, `--surface` bg
- Main area: flex-1, `--bg` bg
- Chat pinned at bottom, messages scroll above

### Tablet (768px–1023px)

- Sidebar collapses to 48px icon strip
- Main area full width
- Navigation via icons only

### Mobile (<768px)

- No sidebar — bottom tab bar for navigation
- Chat is full-screen
- Input stays above keyboard

## Components

### Chat message bubble

- **User:** right-aligned, `--user-bubble` bg, border-radius 12px (bottom-right 2px)
- **Agent:** left-aligned, no bg, 24px circular avatar (`💰` on `--accent`), agent name "Finwise" above message

### Structured response — Expense list

- Embedded table inside agent message area
- Header row: `--border` bg, muted text
- Rows with subtle dividers
- Total line below table

### Structured response — Single expense confirmation

- Key-value pairs in bordered card
- Amount, Merchant, Category, Date

### Structured response — Budget

- Thin progress bar (4px height)
- Percentage + remaining amount inline

### Chat input

- Single-line textarea, auto-grows to max 120px
- `--surface` bg, 1px `--border`, 8px radius
- Enter sends, Shift+Enter newline
- Disabled/loading state: dimmed + spinner

### Sidebar nav items

- Active: `--accent` bg, white text, 6px radius
- Hover: `--border` bg
- Icon + label, 40px height

### Empty states

- Centered text, 1–2 sentences
- CTA button below if applicable
- No illustrations — clear copy only

## Pages

### Chat (default route)

- Full conversation view
- Structured responses render inline
- Agent activity indicators ("Searching your expenses...")
- Auto-scroll to latest message
- Message timestamps where useful
- Streaming responses via SSE

### Expenses (`/expenses`)

- Table: Merchant, Category, Date, Amount
- Filters: date range, category dropdown, merchant search
- Total spending summary at top
- Pagination (20 per page)
- Edit/delete via action menu per row

### Budgets (`/budgets`)

- Placeholder page
- Empty state: "Set a budget through the assistant."
- Future: budget cards with progress bars

### Insights (`/insights`)

- Placeholder page
- Empty state: "Insights will appear once you have spending data."
- Future: monthly trend, top categories, budget utilization

### Settings (`/settings`)

- Placeholder page
- Future: currency preferences, data export

## Chat Experience

- User messages: avatar-less, right-aligned bubbles
- Agent messages: avatar + name label, left-aligned
- Support markdown rendering in agent messages
- Loading state: three-dot animation while agent thinks
- Error state: inline error with retry button
- Auto-scroll to newest message
- SSE streaming for real-time token delivery

## Agent Activity

Visible activity indicators without exposing chain-of-thought:
- "Searching your expenses..."
- "Recording your expense..."
- "Finding matching transactions..."

Then show the final result.

## Empty States

- **No expenses:** "Your spending story starts here." + CTA to chat
- **No budgets:** "Set a budget through the assistant."
- **No conversations:** "Tell me what you spent." in chat input placeholder
- **No insights:** "Insights will appear once you have spending data."

## Responsive Behavior

- Sidebar → icon strip → bottom tab bar
- Expense table → stacked cards on mobile
- Chat input pinned above keyboard on mobile
- Filter bar collapses to dropdown on mobile
- All touch targets ≥ 44px

## API Integration

- REST endpoints for expense CRUD and stats
- SSE streaming for chat
- Loading states for all async operations
- Error handling with retry
- Empty state handling
- No hardcoded data — all from backend

## Tech Stack

- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- Inter font (next/font/google)
- No additional UI libraries
