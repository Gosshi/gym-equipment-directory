"""Normalized equipment alias mapping for municipal ingest."""

from __future__ import annotations

from typing import Final

EQUIPMENT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "treadmill": (
        "トレッドミル",
        "ランニングマシン",
        "ランニングマシーン",
        "トレッドミル(ランニング)",
    ),
    "upright-bike": (
        "アップライトバイク",
        "エアロバイク",
        "バイク",
    ),
    "recumbent-bike": (
        "リカンベントバイク",
        "リカンベントタイプバイク",
    ),
    "arc-trainer": (
        "アークトレーナー",
        "アークトレイナー",
    ),
    "stepper": (
        "ステッパー",
        "ステアクライマー",
    ),
    "lat-pulldown": (
        "ラットプル",
        "ラットプルダウン",
        "ラットプルダウンマシン",
        "ラットプルー",
        "ラットプル/ロウ",
        "VR1ラットプルダウン",
    ),
    "seated-row": (
        "ロウ",
        "シーテッドロー",
        "シーテッドロウ",
        "ラットロウ",
    ),
    "pec-deck-rear-delt": (
        "ペックデック",
        "ペックデックフライ",
        "リアデルト",
        "フライ・リアデルト",
    ),
    "leg-press": (
        "レッグプレス",
        "VR1レッグプレス",
    ),
    "leg-curl": (
        "レッグカール",
        "VR1レッグカール",
    ),
    "leg-extension": (
        "レッグエクステンション",
        "VR1レッグエクステンション",
    ),
    "glute": (
        "グルート",
        "グルートトレーナー",
    ),
    "chest-press": (
        "チェストプレス",
        "チェストプレスマシン",
    ),
    "shoulder-press": (
        "ショルダープレス",
        "ショルダープレスマシン",
    ),
    "torso-rotation": (
        "トーソローテーション",
        "トルソーローテーション",
    ),
    "ab-back-combo": (
        "アブドミナル・バックエクステンション",
        "アブバックコンボ",
        "アブ/バック",
    ),
    "crunch-machine": (
        "クランチャー",
        "アブドミナルクランチャー",
    ),
    "back-extension": (
        "バックエクステンション",
        "バックエクステンションマシン",
    ),
    "smith-machine": (
        "スミスマシン",
        "スミス",
        "スミスプレス",
    ),
    "bench-press": (
        "ベンチプレス",
        "ベンチプレス台",
    ),
    "adjustable-bench": (
        "アジャスタブルベンチ",
        "可変式ベンチ",
    ),
    "functional-trainer": (
        "ファンクショナルトレーナー",
        "ケーブルマシン",
        "BRAVO PRO",
        "ブラボープロ",
        "ケーブルクロス",
    ),
    "dumbbell": (
        "ダンベル",
        "ダンベルセット",
    ),
    "barbell": (
        "バーベル",
        "バーベルセット",
    ),
    "power-rack": (
        "パワーラック",
        "スミス/パワーラック",
    ),
    "squat-rack": (
        "スクワットラック",
        "ハーフラック",
    ),
    "treadmill-curve": (
        "カーブトレッドミル",
        "カーブトレッドミルマシン",
    ),
    "rowing-machine": (
        "ローイングマシン",
        "ローイング",
    ),
    "arc-trainer-stepper": (
        "アークトレーナー/ステッパー",
        "アークトレーナー・ステッパー",
    ),
}


__all__ = ["EQUIPMENT_ALIASES"]
