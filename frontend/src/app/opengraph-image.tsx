import { ImageResponse } from "next/og";

export const alt = "Stock Intelligence: live prices, stock research and portfolio tracking";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const features = ["Live prices", "Stock research", "Price charts", "Watchlists", "Portfolio tracking"];

// Preview card shown when the site link is shared (LinkedIn, Slack, messaging apps).
export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          background: "linear-gradient(135deg, #070b14 0%, #0d1726 60%, #0b2a2a 100%)",
          color: "#f1f5f9",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 14,
              background: "#2ee6c1",
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "center",
              gap: 8,
              paddingBottom: 16,
            }}
          >
            <div style={{ width: 8, height: 18, borderRadius: 4, background: "#08111f" }} />
            <div style={{ width: 8, height: 32, borderRadius: 4, background: "#08111f" }} />
            <div style={{ width: 8, height: 24, borderRadius: 4, background: "#08111f" }} />
          </div>
          <div style={{ fontSize: 34, fontWeight: 600 }}>Stock Intelligence</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 64, fontWeight: 700, lineHeight: 1.1, maxWidth: 980 }}>
            Live prices, stock research and portfolio tracking
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
            {features.map((feature) => (
              <div
                key={feature}
                style={{
                  fontSize: 26,
                  padding: "10px 22px",
                  borderRadius: 999,
                  border: "2px solid #1f3a44",
                  color: "#a5f3e4",
                }}
              >
                {feature}
              </div>
            ))}
          </div>
        </div>

        <div style={{ fontSize: 24, color: "#94a3b8" }}>Next.js · FastAPI · PostgreSQL · Finnhub · Docker</div>
      </div>
    ),
    size,
  );
}
