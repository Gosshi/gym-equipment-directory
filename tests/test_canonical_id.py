from app.services.canonical import make_canonical_id, normalize_name


def test_normalize_name_variants_share_canonical_id() -> None:
    base_pref = "tokyo"
    base_city = "koto"
    names = [
        "施設案内 ｜ ダミージム ｜江東区",
        "施設案内 | ダミージム | 江東区",
        "ダミージム｜江東区",
        "　ダミージム　",
        "ﾀﾞﾐｰｼﾞﾑ",
        "ダミージム\x00",
    ]

    canonical_ids = {make_canonical_id(base_pref, base_city, name) for name in names}

    assert len(canonical_ids) == 1


def test_normalize_name_trims_patterns() -> None:
    assert normalize_name("施設案内 | ジムA | 江東区") == "ジムA"
    assert normalize_name("ジムB｜江東区") == "ジムB"
