import Supercluster from "supercluster";

import type { NearbyGym } from "@/types/gym";

type PointFeature = GeoJSON.Feature<
  GeoJSON.Point,
  {
    gymId: number;
  }
>;

type SuperclusterFeature = GeoJSON.Feature<
  GeoJSON.Point,
  {
    cluster: true;
    cluster_id: number;
    point_count: number;
    point_count_abbreviated?: string;
  }
>;

type ClusterInput = GeoJSON.Feature<
  GeoJSON.Point,
  {
    gymId?: number;
  }
>;

export type MapBounds = {
  north: number;
  south: number;
  east: number;
  west: number;
};

export type ClusterMarker = {
  type: "cluster";
  id: number;
  count: number;
  coordinates: [number, number];
};

export type GymMarker = {
  type: "gym";
  id: number;
  gym: NearbyGym;
  coordinates: [number, number];
};

export type MapMarker = ClusterMarker | GymMarker;

type ClusterTree =
  | {
      type: "cluster";
      index: Supercluster<{ gymId?: number }>;
      gymById: Map<number, NearbyGym>;
      pointFeatures: PointFeature[];
      shouldCluster: true;
    }
  | {
      type: "points";
      gymById: Map<number, NearbyGym>;
      pointFeatures: PointFeature[];
      shouldCluster: false;
    };

const DEFAULT_CLUSTER_RADIUS = 60;
const DEFAULT_CLUSTER_MIN_POINTS = 2;
const DEFAULT_CLUSTER_MAX_ZOOM = 19;

const toPointFeature = (gym: NearbyGym): PointFeature => ({
  type: "Feature",
  geometry: {
    type: "Point",
    coordinates: [gym.longitude, gym.latitude],
  },
  properties: {
    gymId: gym.id,
  },
});

export interface CreateClusterIndexOptions {
  minClusterCount?: number;
  radius?: number;
  minPoints?: number;
  maxZoom?: number;
}

export const createGymClusterIndex = (
  gyms: NearbyGym[],
  {
    minClusterCount = 50,
    radius = DEFAULT_CLUSTER_RADIUS,
    minPoints = DEFAULT_CLUSTER_MIN_POINTS,
    maxZoom = DEFAULT_CLUSTER_MAX_ZOOM,
  }: CreateClusterIndexOptions = {},
): ClusterTree => {
  const validGyms = gyms.filter(
    gym => Number.isFinite(gym.latitude) && Number.isFinite(gym.longitude),
  );
  const pointFeatures = validGyms.map(toPointFeature);
  const gymById = new Map(validGyms.map(gym => [gym.id, gym] as const));

  const shouldCluster = pointFeatures.length >= minClusterCount;

  if (!shouldCluster) {
    return {
      type: "points",
      gymById,
      pointFeatures,
      shouldCluster: false,
    };
  }

  const index = new Supercluster<{ gymId?: number }>({
    radius,
    minPoints,
    maxZoom,
  });

  index.load(pointFeatures as ClusterInput[]);

  return {
    type: "cluster",
    index,
    gymById,
    pointFeatures,
    shouldCluster: true,
  };
};

const toBBox = (bounds: MapBounds): [number, number, number, number] => [
  bounds.west,
  bounds.south,
  bounds.east,
  bounds.north,
];

export const getMarkersForBounds = (
  tree: ClusterTree,
  bounds: MapBounds,
  zoom: number,
): MapMarker[] => {
  if (tree.shouldCluster && tree.type === "cluster") {
    const roundedZoom = Number.isFinite(zoom) ? Math.max(0, Math.round(zoom)) : 0;
    const features = tree.index.getClusters(toBBox(bounds), roundedZoom);

    const markers: MapMarker[] = [];

    for (const feature of features) {
      const coordinates = feature.geometry.coordinates as [number, number];
      const props = feature.properties as Record<string, unknown> | undefined;
      if (props && "cluster" in props && (props as { cluster?: boolean }).cluster) {
        const clusterFeature = feature as SuperclusterFeature;
        markers.push({
          type: "cluster",
          id: clusterFeature.properties.cluster_id,
          count: clusterFeature.properties.point_count,
          coordinates,
        });
        continue;
      }

      const gymId = (feature.properties as { gymId?: number })?.gymId;
      if (!gymId) {
        continue;
      }
      const gym = tree.gymById.get(gymId);
      if (!gym) {
        continue;
      }
      markers.push({ type: "gym", id: gymId, gym, coordinates });
    }

    return markers;
  }

  return tree.pointFeatures
    .map(feature => {
      const gymId = feature.properties.gymId;
      const gym = tree.gymById.get(gymId);
      if (!gym) {
        return null;
      }
      return {
        type: "gym" as const,
        id: gymId,
        gym,
        coordinates: feature.geometry.coordinates as [number, number],
      };
    })
    .filter((value): value is GymMarker => value !== null);
};

export const getClusterExpansionZoom = (tree: ClusterTree, clusterId: number): number | null => {
  if (tree.type !== "cluster") {
    return null;
  }
  try {
    const zoom = tree.index.getClusterExpansionZoom(clusterId);
    return Number.isFinite(zoom) ? zoom : null;
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      // eslint-disable-next-line no-console
      console.warn("Failed to get cluster expansion zoom", error);
    }
    return null;
  }
};

export const getClusterPointCount = (tree: ClusterTree): number => tree.pointFeatures.length;
