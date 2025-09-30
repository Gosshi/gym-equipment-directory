export interface MetaOption {
  value: string;
  label: string;
}

export type PrefectureOption = MetaOption;
export type CityOption = MetaOption;

export interface EquipmentOption extends MetaOption {
  slug: string;
  name: string;
  category: string | null;
}
