import { ImageResponse } from "next/og";

import { getGymBySlug } from "@/services/gyms";

export const runtime = "edge";

export const alt = "Gym Detail";
export const size = {
  width: 1200,
  height: 630,
};

export const contentType = "image/png";

export default async function Image({ params }: { params: { slug: string } }) {
  try {
    const gym = await getGymBySlug(params.slug);

    return new ImageResponse(
      (
        <div
          style={{
            height: "100%",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#09090b", // zinc-950
            color: "#fafafa", // zinc-50
            fontFamily: '"Noto Sans JP", sans-serif',
            position: "relative",
          }}
        >
          {/* Background Pattern */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage:
                "radial-gradient(circle at 25px 25px, #27272a 2%, transparent 0%), radial-gradient(circle at 75px 75px, #27272a 2%, transparent 0%)",
              backgroundSize: "100px 100px",
              opacity: 0.5,
            }}
          />

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 10,
              padding: "40px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: 32,
                fontWeight: "bold",
                color: "#a1a1aa", // zinc-400
                marginBottom: 20,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
              }}
            >
              IRON MAP
            </div>

            <div
              style={{
                fontSize: 64,
                fontWeight: 900,
                lineHeight: 1.2,
                marginBottom: 20,
                backgroundImage: "linear-gradient(to bottom right, #ffffff, #a1a1aa)",
                backgroundClip: "text",
                color: "transparent",
                maxWidth: "1000px",
                wordBreak: "break-word",
              }}
            >
              {gym.name}
            </div>

            <div
              style={{
                fontSize: 36,
                color: "#e4e4e7", // zinc-200
                marginBottom: 40,
                display: "flex",
                alignItems: "center",
                gap: "16px",
              }}
            >
              <span>{gym.prefecture}</span>
              <span style={{ color: "#52525b" }}>/</span>
              <span>{gym.city}</span>
            </div>

            {gym.equipments.length > 0 && (
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  justifyContent: "center",
                  gap: "16px",
                  maxWidth: "900px",
                }}
              >
                {gym.equipments.slice(0, 6).map((equip, i) => (
                  <div
                    key={i}
                    style={{
                      backgroundColor: "#27272a", // zinc-800
                      color: "#e4e4e7", // zinc-200
                      padding: "12px 24px",
                      borderRadius: "9999px",
                      fontSize: 24,
                      border: "1px solid #3f3f46", // zinc-700
                    }}
                  >
                    {equip}
                  </div>
                ))}
                {gym.equipments.length > 6 && (
                  <div
                    style={{
                      backgroundColor: "transparent",
                      color: "#a1a1aa", // zinc-400
                      padding: "12px 24px",
                      fontSize: 24,
                    }}
                  >
                    +{gym.equipments.length - 6} more
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ),
      {
        ...size,
      },
    );
  } catch (e) {
    return new ImageResponse(
      (
        <div
          style={{
            height: "100%",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#09090b",
            color: "#fafafa",
          }}
        >
          <div style={{ fontSize: 64, fontWeight: "bold" }}>IRON MAP</div>
        </div>
      ),
      { ...size },
    );
  }
}
