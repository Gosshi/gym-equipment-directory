# Favorites Feature (Step 5)

## Overview
- Adds a toggleable "お気に入り" button to `/gyms/[slug]` that syncs with the backend API.
- Provides a new `/me/favorites` page that lists registered gyms with quick access links and removal
  controls.
- Shares state between pages through the `useFavorites()` hook, enabling optimistic UI updates and a
  single source of truth.

## API Contract
| Method | Endpoint | Notes |
| ------ | -------- | ----- |
| `GET` | `/me/favorites` | Returns `{ items: GymSummary[] }`. |
| `POST` | `/me/favorites` | Body: `{ "gymId": number }`. Idempotent. |
| `DELETE` | `/me/favorites/{gymId}` | Removes the relation. Also idempotent. |

- Calls are authenticated (Bearer token) when a user session exists. Unauthenticated clients rely on
  local storage only.
- Error responses propagate via `ApiError` and surface through toast notifications and inline
  messaging when relevant.

## Frontend Architecture
- `@/store/favoritesStore` exposes `useFavorites()` backed by Zustand.
  - Hydrates from local storage (`GED_FAVORITES`) for guests and keeps optimistic state in sync with
    the API when signed in.
  - Tracks pending gym ids for optimistic UI, handles background refreshes, and stores the latest
    server snapshot back to local storage after successful mutations/syncs.
- `/me/favorites` page and gym detail screens consume the shared store for optimistic updates.
- Toast notifications (Shadcn + Radix) are wired through `Toaster` in `app/layout.tsx`, and the
  toggle actions trigger success/error feedback without blocking user interaction.

## UI Details
- **Gym detail**: The button reflects current membership, disables while the mutation is pending, and
  shows toast feedback for both add/remove flows.
- **Favorites page (`/me/favorites`)**:
  - Sorts entries by `createdAt` (newest first) when available, and displays a fallback message when
    the timestamp is missing.
  - Provides quick navigation to gym detail pages and removal controls with optimistic updates.
  - Includes skeletons, empty/error states, and a manual refresh button (useful when testing the API
    without reloading the route).

## Known Limitations & Follow-ups
- The backend schema currently omits richer metadata (ratings, equipment list, etc.) for favorites,
  so cards display what is available and fall back gracefully when fields are `null`.
- Toasts rely on client rendering; server-side rendering of routes that reference `useFavorites`
  should continue to use the client boundary pattern adopted here.
- Additional automated coverage for the `/me/favorites` page (e.g., optimistic removal snapshot
  tests) can be added once the UI stabilises.
