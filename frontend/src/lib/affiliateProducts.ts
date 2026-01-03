/**
 * カテゴリ別おすすめ商品データ
 *
 * アフィリエイトリンクの設定:
 * - 楽天: NEXT_PUBLIC_RAKUTEN_AFFILIATE_ID 環境変数を設定
 * - Amazon: NEXT_PUBLIC_AMAZON_ASSOCIATE_TAG 環境変数を設定
 *
 * 環境変数が未設定の場合、リンクは表示されません。
 */

export interface Product {
  id: string;
  name: string;
  description: string;
  /** 楽天商品検索キーワード */
  rakutenKeyword: string;
  /** Amazon検索キーワード */
  amazonKeyword: string;
}

export interface CategoryProducts {
  categoryLabel: string;
  products: Product[];
}

// カテゴリ別おすすめ商品定義
export const CATEGORY_PRODUCTS: Record<string, CategoryProducts> = {
  gym: {
    categoryLabel: "ジム",
    products: [
      {
        id: "gym-gloves",
        name: "トレーニンググローブ",
        description: "手のひらを保護し、グリップ力を向上",
        rakutenKeyword: "トレーニンググローブ ジム",
        amazonKeyword: "トレーニンググローブ",
      },
      {
        id: "gym-belt",
        name: "トレーニングベルト",
        description: "腰をサポートし、安全にトレーニング",
        rakutenKeyword: "トレーニングベルト 筋トレ",
        amazonKeyword: "トレーニングベルト",
      },
      {
        id: "gym-protein",
        name: "プロテイン",
        description: "トレーニング後の栄養補給に",
        rakutenKeyword: "プロテイン ホエイ",
        amazonKeyword: "プロテイン ホエイ",
      },
      {
        id: "gym-shaker",
        name: "プロテインシェイカー",
        description: "ジムに持っていける便利なシェイカー",
        rakutenKeyword: "プロテインシェイカー",
        amazonKeyword: "プロテインシェイカー",
      },
    ],
  },
  pool: {
    categoryLabel: "プール",
    products: [
      {
        id: "pool-goggles",
        name: "スイミングゴーグル",
        description: "曇りにくく、視界クリア",
        rakutenKeyword: "スイミングゴーグル 競泳",
        amazonKeyword: "スイミングゴーグル",
      },
      {
        id: "pool-cap",
        name: "スイムキャップ",
        description: "シリコン製で髪を守る",
        rakutenKeyword: "スイムキャップ シリコン",
        amazonKeyword: "スイムキャップ シリコン",
      },
      {
        id: "pool-towel",
        name: "セームタオル",
        description: "吸水性抜群、コンパクトに持ち運び",
        rakutenKeyword: "セームタオル 水泳",
        amazonKeyword: "セームタオル 水泳",
      },
      {
        id: "pool-bag",
        name: "防水バッグ",
        description: "濡れた水着や道具を収納",
        rakutenKeyword: "防水バッグ プール",
        amazonKeyword: "防水バッグ スイミング",
      },
    ],
  },
  court: {
    categoryLabel: "テニスコート",
    products: [
      {
        id: "tennis-balls",
        name: "テニスボール",
        description: "練習用ボールセット",
        rakutenKeyword: "テニスボール 練習",
        amazonKeyword: "テニスボール",
      },
      {
        id: "tennis-grip",
        name: "グリップテープ",
        description: "汗を吸収し、滑りにくい",
        rakutenKeyword: "テニス グリップテープ",
        amazonKeyword: "テニス グリップテープ",
      },
      {
        id: "tennis-wristband",
        name: "リストバンド",
        description: "汗を吸収、快適にプレー",
        rakutenKeyword: "テニス リストバンド",
        amazonKeyword: "テニス リストバンド",
      },
      {
        id: "tennis-bag",
        name: "ラケットバッグ",
        description: "ラケットと道具をまとめて収納",
        rakutenKeyword: "テニス ラケットバッグ",
        amazonKeyword: "テニス ラケットバッグ",
      },
    ],
  },
  hall: {
    categoryLabel: "体育館",
    products: [
      {
        id: "hall-shoes",
        name: "体育館シューズ",
        description: "室内スポーツに最適なシューズ",
        rakutenKeyword: "体育館シューズ 室内",
        amazonKeyword: "体育館シューズ",
      },
      {
        id: "hall-shuttle",
        name: "バドミントンシャトル",
        description: "練習用シャトルセット",
        rakutenKeyword: "バドミントン シャトル 練習",
        amazonKeyword: "バドミントン シャトル",
      },
      {
        id: "hall-tape",
        name: "テーピング",
        description: "怪我予防とサポートに",
        rakutenKeyword: "テーピング スポーツ",
        amazonKeyword: "テーピング スポーツ",
      },
      {
        id: "hall-kneepads",
        name: "膝サポーター",
        description: "膝を守り、安心してプレー",
        rakutenKeyword: "膝サポーター バレー",
        amazonKeyword: "膝サポーター スポーツ",
      },
    ],
  },
  field: {
    categoryLabel: "グラウンド",
    products: [
      {
        id: "field-glove",
        name: "野球グローブ",
        description: "キャッチボールから試合まで",
        rakutenKeyword: "野球 グローブ 一般",
        amazonKeyword: "野球 グローブ",
      },
      {
        id: "field-spikes",
        name: "スパイク",
        description: "グラウンドでのグリップ力を確保",
        rakutenKeyword: "野球 スパイク",
        amazonKeyword: "野球 スパイク",
      },
      {
        id: "field-ball",
        name: "サッカーボール",
        description: "練習用ボール",
        rakutenKeyword: "サッカーボール 練習",
        amazonKeyword: "サッカーボール",
      },
      {
        id: "field-bag",
        name: "スポーツバッグ",
        description: "道具をまとめて持ち運び",
        rakutenKeyword: "スポーツバッグ 野球",
        amazonKeyword: "スポーツバッグ 大容量",
      },
    ],
  },
  martial_arts: {
    categoryLabel: "武道場",
    products: [
      {
        id: "martial-judogi",
        name: "柔道着",
        description: "練習用柔道着セット",
        rakutenKeyword: "柔道着 練習用",
        amazonKeyword: "柔道着",
      },
      {
        id: "martial-shinai",
        name: "竹刀",
        description: "剣道の稽古に",
        rakutenKeyword: "竹刀 剣道",
        amazonKeyword: "竹刀 剣道",
      },
      {
        id: "martial-supporter",
        name: "サポーター",
        description: "関節を保護",
        rakutenKeyword: "武道 サポーター",
        amazonKeyword: "格闘技 サポーター",
      },
      {
        id: "martial-bag",
        name: "道着バッグ",
        description: "道着を収納して持ち運び",
        rakutenKeyword: "道着 バッグ",
        amazonKeyword: "道着 バッグ",
      },
    ],
  },
  archery: {
    categoryLabel: "弓道場",
    products: [
      {
        id: "archery-kake",
        name: "弓がけ（ゆがけ）",
        description: "弦から指を保護",
        rakutenKeyword: "弓道 かけ",
        amazonKeyword: "弓道 かけ",
      },
      {
        id: "archery-hakama",
        name: "弓道着",
        description: "稽古用弓道着セット",
        rakutenKeyword: "弓道着 セット",
        amazonKeyword: "弓道着",
      },
      {
        id: "archery-giriko",
        name: "ぎり粉",
        description: "かけの滑り止めに",
        rakutenKeyword: "弓道 ぎり粉",
        amazonKeyword: "弓道 ぎり粉",
      },
      {
        id: "archery-bag",
        name: "矢筒",
        description: "矢を安全に持ち運び",
        rakutenKeyword: "弓道 矢筒",
        amazonKeyword: "弓道 矢筒",
      },
    ],
  },
};

import { AFFILIATE_LINKS } from "@/config/affiliate";

/**
 * カテゴリ配列から最初にマッチするおすすめ商品を取得
 */
export function getProductsForCategories(categories: string[]): CategoryProducts | null {
  for (const category of categories) {
    if (CATEGORY_PRODUCTS[category]) {
      return CATEGORY_PRODUCTS[category];
    }
  }
  return null;
}

/**
 * 楽天検索URLを生成
 */
export function buildRakutenSearchUrl(keyword: string): string | null {
  const affiliateId = process.env.NEXT_PUBLIC_RAKUTEN_AFFILIATE_ID;
  if (!affiliateId) {
    return null;
  }
  const encodedKeyword = encodeURIComponent(keyword);
  return `https://hb.afl.rakuten.co.jp/ichiba/${affiliateId}/?pc=https://search.rakuten.co.jp/search/mall/${encodedKeyword}/`;
}

/**
 * Amazon検索URLを生成
 */
export function buildAmazonSearchUrl(keyword: string): string | null {
  const associateTag = process.env.NEXT_PUBLIC_AMAZON_ASSOCIATE_TAG;
  if (!associateTag) {
    return null;
  }
  const encodedKeyword = encodeURIComponent(keyword);
  return `https://www.amazon.co.jp/s?k=${encodedKeyword}&tag=${associateTag}`;
}

/**
 * アフィリエイトが有効かどうか
 */
export function isAffiliateEnabled(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_RAKUTEN_AFFILIATE_ID || process.env.NEXT_PUBLIC_AMAZON_ASSOCIATE_TAG,
  );
}

export type ContextualGym = {
  category?: string | null;
  categories?: string[];
  equipments?: string[];
  poolLanes?: number | null;
  pools?: Array<{ lanes?: number | null }>;
  hallSports?: string[];
  hallAreaSqm?: number | null;
};

export type ContextualAdLink = {
  id: string;
  label: string;
  href: string;
  isAffiliate?: boolean;
};

export type ContextualAdGroup = {
  key: string;
  title: string;
  description: string;
  links: ContextualAdLink[];
};

type GroupKey = "pool" | "gym" | "hall" | "dojo";

type UtmParams = {
  source: string;
  medium: string;
  campaign: string;
  content?: string;
  term?: string;
};

type PartnerLinkConfig = {
  id: string;
  label: string;
  url: string;
  utmContent: string;
  isAffiliate?: boolean;
};

type AffiliateItemConfig = {
  id: string;
  label: string;
  keyword: string;
};

type ContextualAdGroupConfig = {
  key: GroupKey;
  title: string;
  description: string;
  links?: PartnerLinkConfig[];
  affiliateItems?: AffiliateItemConfig[];
};

const MAX_CONTEXTUAL_AD_GROUPS = 2;
const BASE_UTM: Pick<UtmParams, "source" | "medium"> = {
  source: "spomap",
  medium: "contextual_ad",
};

const CONTEXTUAL_AD_CONFIG: Record<GroupKey, ContextualAdGroupConfig> = {
  pool: {
    key: "pool",
    title: "プール利用に必要なもの",
    description: "当日忘れてもすぐに探せる定番アイテム",
    affiliateItems: [
      { id: "swimcap", label: "スイムキャップ", keyword: "スイムキャップ シリコン" },
      {
        id: "goggles",
        label: "スイミングゴーグル",
        keyword: "スイミングゴーグル 曇り止め",
      },
    ],
  },
  gym: {
    key: "gym",
    title: "スポーツウェア・用品を揃える",
    description: "人気のスポーツブランドや機能性ウェアをチェック",
    links: [
      {
        id: "xebio",
        label: "ゼビオオンラインストアで探す",
        url: AFFILIATE_LINKS.XEBIO,
        utmContent: "xebio",
        isAffiliate: true,
      },
      {
        id: "murasaki",
        label: "ムラサキスポーツで探す",
        url: AFFILIATE_LINKS.MURASAKI_SPORTS,
        utmContent: "murasaki",
        isAffiliate: true,
      },
    ],
  },
  hall: {
    key: "hall",
    title: "貸切コートを探す",
    description: "抽選に外れたら民間レンタルコートを検討",
    links: [
      {
        id: "spacemarket",
        label: "スペースマーケットで探す",
        url: AFFILIATE_LINKS.SPACEMARKET,
        utmContent: "spacemarket",
        isAffiliate: true,
      },
      {
        id: "instabase",
        label: "インスタベースで探す",
        url: AFFILIATE_LINKS.INSTABASE,
        utmContent: "instabase",
        isAffiliate: true,
      },
    ],
  },
  dojo: {
    key: "dojo",
    title: "子ども向けスポーツスクールの体験",
    description: "近くの教室を比較して予約",
    links: [], // アフィリエイトがないため一時的に非表示
  },
};

const applyUtm = (url: string, params: UtmParams): string => {
  try {
    const parsed = new URL(url);
    parsed.searchParams.set("utm_source", params.source);
    parsed.searchParams.set("utm_medium", params.medium);
    parsed.searchParams.set("utm_campaign", params.campaign);
    if (params.content) {
      parsed.searchParams.set("utm_content", params.content);
    }
    if (params.term) {
      parsed.searchParams.set("utm_term", params.term);
    }
    return parsed.toString();
  } catch {
    return url;
  }
};

const buildPartnerLinks = (key: GroupKey, links: PartnerLinkConfig[]): ContextualAdLink[] => {
  return links.map(link => ({
    id: link.id,
    label: link.label,
    href: link.isAffiliate
      ? link.url // アフィリエイトリンクはUTM付与せずそのまま使う
      : applyUtm(link.url, {
          ...BASE_UTM,
          campaign: key,
          content: link.utmContent,
        }),
    isAffiliate: link.isAffiliate,
  }));
};

const buildAffiliateLinks = (items: AffiliateItemConfig[]): ContextualAdLink[] => {
  if (!isAffiliateEnabled()) {
    return [];
  }

  const links: ContextualAdLink[] = [];
  for (const item of items) {
    const rakutenUrl = buildRakutenSearchUrl(item.keyword);
    const amazonUrl = buildAmazonSearchUrl(item.keyword);

    if (rakutenUrl) {
      links.push({
        id: `${item.id}-rakuten`,
        label: `${item.label}を楽天で探す`,
        href: rakutenUrl,
        isAffiliate: true,
      });
    }
    if (amazonUrl) {
      links.push({
        id: `${item.id}-amazon`,
        label: `${item.label}をAmazonで探す`,
        href: amazonUrl,
        isAffiliate: true,
      });
    }
  }

  return links;
};

const collectCategories = (gym: ContextualGym) => {
  const values = new Set<string>();
  const add = (value?: string | null) => {
    if (!value) {
      return;
    }
    values.add(value.trim().toLowerCase());
  };
  add(gym.category);
  gym.categories?.forEach(add);
  return values;
};

export const resolveContextualAdGroups = (gym: ContextualGym): ContextualAdGroup[] => {
  const categories = collectCategories(gym);
  const hasCategory = categories.size > 0 || Boolean(gym.category);

  const hasPool =
    categories.has("pool") ||
    (typeof gym.poolLanes === "number" && gym.poolLanes > 0) ||
    (gym.pools?.length ?? 0) > 0;
  const hasGym = categories.has("gym") || (!hasCategory && (gym.equipments?.length ?? 0) > 0);
  const hasHall =
    categories.has("hall") ||
    categories.has("arena") ||
    (gym.hallSports?.length ?? 0) > 0 ||
    (typeof gym.hallAreaSqm === "number" && gym.hallAreaSqm > 0);
  const hasDojo =
    categories.has("martial_arts") || categories.has("dojo") || categories.has("archery");

  const groups: ContextualAdGroup[] = [];
  const pushGroup = (key: GroupKey) => {
    const config = CONTEXTUAL_AD_CONFIG[key];
    const links = [
      ...(config.links ? buildPartnerLinks(key, config.links) : []),
      ...(config.affiliateItems ? buildAffiliateLinks(config.affiliateItems) : []),
    ];

    if (links.length === 0) {
      return;
    }

    groups.push({
      key: config.key,
      title: config.title,
      description: config.description,
      links,
    });
  };

  if (hasPool) {
    pushGroup("pool");
  }
  if (hasGym) {
    pushGroup("gym");
  }
  if (hasHall) {
    pushGroup("hall");
  }
  if (hasDojo) {
    pushGroup("dojo");
  }

  return groups.slice(0, MAX_CONTEXTUAL_AD_GROUPS);
};
