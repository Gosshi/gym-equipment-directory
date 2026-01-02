import { ImageResponse } from "next/og";
import { getGymBySlug } from "@/services/gyms";

export const runtime = "edge";

export const alt = "Gym Details";
export const size = {
  width: 1200,
  height: 630,
};

export const contentType = "image/png";

export default async function Image({ params }: { params: { slug: string[] } }) {
  const { slug: slugParts } = await params;
  const slug = slugParts.join("/");
  const gym = await getGymBySlug(slug);

  if (!gym) {
    return new ImageResponse(
      (
        <div
          style={{
            fontSize: 48,
            background: "white",
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          SPOMAP
        </div>
      ),
      {
        ...size,
      },
    );
  }

  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(to bottom right, #1a1a1a, #2a2a2a)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          fontFamily: "sans-serif",
          padding: "40px",
          textAlign: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "20px",
          }}
        >
          <div
            style={{
              width: "20px",
              height: "20px",
              background: "#FFD700",
              marginRight: "10px",
              borderRadius: "50%",
            }}
          />
          <div style={{ fontSize: 24, fontWeight: "bold", color: "#FFD700" }}>SPOMAP</div>
        </div>
        <div
          style={{
            fontSize: 60,
            fontWeight: 900,
            marginBottom: "20px",
            lineHeight: 1.2,
          }}
        >
          {gym.name}
        </div>
        <div style={{ fontSize: 30, color: "#cccccc" }}>
          {gym.prefecture} {gym.city}
        </div>
        {gym.equipments.length > 0 && (
          <div
            style={{
              display: "flex", // Note: flex-wrap is not strictly supported in satori basic, but row is
              marginTop: "40px",
              gap: "10px",
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            {gym.equipments.slice(0, 5).map((eq, i) => (
              <div
                key={i}
                style={{
                  background: "rgba(255, 255, 255, 0.1)",
                  padding: "10px 20px",
                  borderRadius: "20px",
                  fontSize: 20,
                  whiteSpace: "nowrap",
                }}
              >
                {eq}
              </div>
            ))}
          </div>
        )}
      </div>
    ),
    {
      ...size,
    },
  );
}
