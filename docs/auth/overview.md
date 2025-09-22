# 認証スキャフォールド概要

このドキュメントでは、フロントエンド (Next.js) 側に追加した認証スキャフォールドと、スタブ認証モードでの動作手順、将来的に OAuth 認証へ差し替える際の想定箇所について整理します。

## モード切り替え

- `NEXT_PUBLIC_AUTH_MODE` で認証モードを切り替えます。現在サポートしている値は `stub` と `oauth` です。
- `.env.example` / `frontend/.env.example` にはデフォルトで `NEXT_PUBLIC_AUTH_MODE=stub` を定義しています。
- OAuth 導入時に利用する環境変数のプレースホルダとして以下を追記しています。
  - `NEXT_PUBLIC_OAUTH_PROVIDER` (例: `github`)
  - `NEXT_PUBLIC_OAUTH_CLIENT_ID`
  - `NEXT_PUBLIC_OAUTH_REDIRECT_URI` (例: `http://127.0.0.1:3000/auth/callback`)

## スタブ認証の挙動

- `frontend/src/auth/authClient.ts` でモードごとの実装を定義しています。`stub` モードでは、`localStorage` に `ged.auth.session` キーでトークンとユーザー情報を保存します。
- サインイン時はニックネームを受け取り、`stub.<uuid>` 形式のダミートークンと、DiceBear の Initials API を用いたアバター URL を生成します。
- サインアウト時は `localStorage` のセッション情報を削除します。
- OAuth モードについては、`/auth/login -> /auth/callback -> /auth/session` を用いたフローを実装予定の TODO コメントを追加しています。

## 共通認証レイヤ

- `frontend/src/auth/AuthProvider.tsx`
  - React Context でユーザー情報 (`User` 型) や `signIn` / `signOut` / `getToken` / `requireAuth` を提供します。
  - プロバイダ自身が `LoginDialog` をレンダリングし、未ログイン状態で `requireAuth` が呼ばれた場合にモーダルを開きます。
- `frontend/src/components/auth/LoginDialog.tsx`
  - スタブモード向けのサインインモーダル。ニックネームを入力してサインインします。
- `frontend/src/components/common/Header.tsx`
  - 右上にログインボタンとユーザーメニュー (アバター / お気に入りリンク / ログアウト) を表示します。
- `frontend/src/lib/apiClient.ts`
  - API リクエスト時に `Authorization: Bearer <token>` ヘッダーを自動付与します (トークン取得は `authClient.getToken()` を経由)。

## ルーティング/アクション保護

- `frontend/src/routes/withAuthGuard.tsx`
  - `useAuthGuard` (alias: `withAuthGuard`) でコールバックをラップし、未ログイン時はログインモーダルを表示します。
  - ジム詳細画面・お気に入り一覧での「お気に入り操作」に適用済みです。

## 型定義

- `frontend/src/types/user.ts` に将来の OAuth でも流用できる最小公倍数の `User` 型を定義しています。

## 今後 OAuth を導入する際の変更ポイント

1. `frontend/src/auth/authClient.ts`
   - `createOAuthClient` 内の TODO を実装し、バックエンドの `/auth/login`・`/auth/callback`・`/auth/session` エンドポイントに接続します。
   - トークン管理を Cookie やセキュアストレージに切り替える場合は `getToken` の戻り値を調整します。
2. `frontend/src/auth/AuthProvider.tsx`
   - OAuth リダイレクト完了後のセッション再取得 (`authClient.getSession`) を追加し、ユーザー情報を再同期します。
   - 必要に応じて CSRF 対策や状態パラメータの取り扱いを追加します。
3. `frontend/src/components/auth/LoginDialog.tsx`
   - OAuth モードでは「外部プロバイダでログイン」ボタン等を表示する実装に差し替えます。
4. API 側
   - `/auth/login` / `/auth/callback` / `/auth/session` / `/auth/logout` などのエンドポイント実装。
   - Bearer トークンを検証し、必要なエンドポイントで 401 を返すように調整します。

## スタブモードでの動作確認手順

1. `.env` または `.env.local` に `NEXT_PUBLIC_AUTH_MODE=stub` を設定します (デフォルトで有効です)。
2. `npm install` (初回のみ) 後、`npm run dev` でフロントエンドを起動します。
3. 画面右上の「ログイン」ボタンからニックネームを入力してサインインします。
4. ジム詳細ページで「お気に入り」ボタンを押すと、ログイン済みであればトースト通知が表示されます。
5. 未ログイン状態で「お気に入り」操作を実行するとログインモーダルが表示されます。
6. ヘッダーのユーザーメニューから「ログアウト」を選ぶとセッションがクリアされます。

これらの仕組みにより、将来 OAuth 認証を導入する際の影響範囲を `authClient` と `AuthProvider` に集約しています。
