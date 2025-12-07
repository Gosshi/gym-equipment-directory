"""Tag aliases for normalizing municipal facility conditions."""

from __future__ import annotations

# Map standardized slug -> list of Japanese keywords
TAG_ALIASES: dict[str, list[str]] = {
    "parking": ["駐車場", "駐車場あり", "有料駐車場", "コインパーキング"],
    "24h": ["24時間", "24時間営業", "24h"],
    "shower": ["シャワー", "シャワールーム", "温水シャワー"],
    "sauna": ["サウナ", "ミストサウナ", "ドライサウナ"],
    "wifi": ["wi-fi", "wifi", "ワイファイ", "無線lan"],
    "powder_room": ["パウダールーム", "化粧室", "メイクルーム"],
    "rental_wear": ["レンタルウェア", "ウェアレンタル", "ウェア貸出"],
    "rental_shoes": ["レンタルシューズ", "シューズレンタル", "シューズ貸出"],
    "rental_towel": ["レンタルタオル", "タオルレンタル", "タオル貸出"],
}
