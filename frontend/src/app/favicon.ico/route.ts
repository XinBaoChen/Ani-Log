const FAVICON_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#ef4444"/>
    </linearGradient>
  </defs>
  <rect x="4" y="4" width="56" height="56" rx="12" fill="#0f172a"/>
  <circle cx="32" cy="32" r="20" fill="url(#g)"/>
  <path d="M20 32h24" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>
  <circle cx="24" cy="24" r="3" fill="#ffffff"/>
  <circle cx="40" cy="40" r="3" fill="#ffffff"/>
</svg>
`;

export function GET() {
  return new Response(FAVICON_SVG.trim(), {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
