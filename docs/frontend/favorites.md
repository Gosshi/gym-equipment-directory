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
| `GET` | `/me/favorites?device_id={id}` | Returns an array of favorites. Each item contains `gym_id`, `slug`, `name`, `pref`, `city`, `last_verified_at`, and may include `address`, `thumbnail_url`, `created_at`. |
| `POST` | `/me/favorites` | Body: `{ "device_id": string, "gym_id": number }`. Idempotent. |
| `DELETE` | `/me/favorites/{gym_id}?device_id={id}` | Removes the relation. Also idempotent. |

- A pseudo user identifier (`device_id`) is generated client-side and persisted to
  `localStorage (gid:favoritesDeviceId)` to satisfy the current anonymous workflow.
- Error responses propagate via `ApiError` and surface through toast notifications and inline
  messaging when relevant.

## Frontend Architecture
- `@/store/favorites` exposes `useFavorites()` which relies on `useSyncExternalStore` to share state
  across components.
  - Handles initial hydration (`listFavorites`), optimistic adds/removals, background refreshes, and
    pending indicators per gym id.
  - Persists/recovers the device identifier, falling back to deterministic generation when the
    storage call fails (private browsing, etc.).
- Services live in `@/services/favorites` and consolidate API interactions with response
  normalisation to the `Favorite` domain model (`src/types/favorite.ts`).
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
- Authentication remains provisional; multiple browsers/devices cannot yet merge favorites for the
  same user identity.
- The backend schema currently omits richer metadata (ratings, equipment list, etc.) for favorites,
  so cards display what is available and fall back gracefully when fields are `null`.
- Toasts rely on client rendering; server-side rendering of routes that reference `useFavorites`
  should continue to use the client boundary pattern adopted here.
- Additional automated coverage for the `/me/favorites` page (e.g., optimistic removal snapshot
  tests) can be added once the UI stabilises.
