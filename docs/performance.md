# パフォーマンス方針

フロントエンドの体感速度とリソース効率を維持するため、軽量な運用で確認できるチェックポイントを整理する。

## 画像と地図リソース

- 画像は WebP または AVIF を優先し、必要に応じて Next.js の最適化を利用する。
- 地図タイルは MapLibre のキャッシュを活用し、ズームレベルごとの取得枚数を抑える設定を検討する。
- ピンアイコンは SVG を利用し、`prefers-reduced-motion` 時はアニメーションを無効化する。

## データフェッチとキャッシュ

- React Query で以下を徹底する。
  - 一覧系は `staleTime` を明示的に設定し、ページング時の再フェッチを最小化する。
  - 現在地ベースの検索は `cacheTime` を短めに設定し、位置が変わった場合の stale データを防ぐ。
- Zustand ストアでは、URL 同期に必要なデータのみ保持し、結果セットは React Query で管理する。

## メモ化と再レンダリング抑制

- 地図コンポーネントには `React.memo` と `useMemo` を適用し、ピン数が多い場合でも再計算を避ける。
- ページネーションコンポーネントは、現在ページ・最大ページが変化した場合のみ再描画されるよう props を整理する。
- 計測時は React DevTools Profiler でレンダリング回数を把握する。

## 手動バンドル分析

- CI では常時実行しない。必要時に手動で以下のスクリプトを追加する想定とする。

```jsonc
// frontend/package.json への追記案（実装は別 PR）
"scripts": {
  "analyze:bundle": "next build && npx source-map-explorer \".next/static/chunks/*.js\""
}
```

- 実行手順
  1. `npm --prefix frontend install` を実行して依存を最新化する。
  2. `npm --prefix frontend run analyze:bundle` を手動で実行し、`source-map-explorer` の結果をスクリーンショットまたは JSON で保存する。
  3. 主要チャンクサイズを Notion または docs/backlog.md に記録し、回帰が疑われる場合は比較する。

## 計測とモニタリング

- Lighthouse（手動）で LCP/FID/CLS のスコアを記録し、地図表示時の遅延が閾値（LCP < 3.0s）を超えないか確認する。
- ページネーション操作時は Performance タイムラインを取得し、API レイテンシとレンダリング時間を分離して評価する。
- バンドルサイズの増加が 10% を超えた場合は、ロードマップ P1/P2 のタスクで優先的に調整する。

## 参考リンク

- [短期ロードマップ](./roadmap-next.md)
- [テスト戦略](./testing-strategy.md)
- [アクセシビリティ指針](./accessibility.md)
- [FE10 改善計画の進捗サマリー](./fe10-progress.md)
