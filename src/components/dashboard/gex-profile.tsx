interface Props {
  profile: [number, number][];
  spot: number | null | undefined;
  flip: number | null | undefined;
  width?: number;
  height?: number;
}

/** Dealer gamma exposure re-priced across a grid of hypothetical spot levels. */
export function GexProfile({ profile, spot, flip, width = 420, height = 150 }: Props) {
  if (!profile || profile.length < 3) {
    return <div className="text-xs text-slate-400">无 Gamma 曲线</div>;
  }
  const xs = profile.map((p) => p[0]);
  const ys = profile.map((p) => p[1]);
  const xmin = Math.min(...xs);
  const xmax = Math.max(...xs);
  const ymax = Math.max(Math.abs(Math.min(...ys)), Math.abs(Math.max(...ys))) || 1;
  const padL = 44;
  const padR = 10;
  const padT = 10;
  const padB = 22;
  const X = (v: number) => padL + ((v - xmin) / (xmax - xmin || 1)) * (width - padL - padR);
  const Y = (v: number) => padT + (1 - (v + ymax) / (2 * ymax)) * (height - padT - padB);
  const path = profile.map((p, i) => `${i === 0 ? "M" : "L"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" ");
  const area = `${path} L${X(xmax).toFixed(1)},${Y(0).toFixed(1)} L${X(xmin).toFixed(1)},${Y(0).toFixed(1)} Z`;
  const ticks = [xmin, (xmin + xmax) / 2, xmax];
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Gamma 曲线" className="max-w-full">
      <defs>
        <clipPath id="gex-pos">
          <rect x={0} y={0} width={width} height={Y(0)} />
        </clipPath>
        <clipPath id="gex-neg">
          <rect x={0} y={Y(0)} width={width} height={height - Y(0)} />
        </clipPath>
      </defs>
      <path d={area} fill="#10b981" fillOpacity={0.18} clipPath="url(#gex-pos)" />
      <path d={area} fill="#f43f5e" fillOpacity={0.18} clipPath="url(#gex-neg)" />
      <line x1={padL} x2={width - padR} y1={Y(0)} y2={Y(0)} stroke="#94a3b8" />
      <path d={path} fill="none" stroke="#0f172a" strokeWidth={1.6} />
      {flip != null && flip >= xmin && flip <= xmax && (
        <g>
          <line x1={X(flip)} x2={X(flip)} y1={padT} y2={height - padB} stroke="#f59e0b" strokeDasharray="4 3" />
          <text x={X(flip) + 3} y={padT + 10} fontSize={10} fill="#b45309">
            翻转 {flip.toFixed(1)}
          </text>
        </g>
      )}
      {spot != null && spot >= xmin && spot <= xmax && (
        <g>
          <line x1={X(spot)} x2={X(spot)} y1={padT} y2={height - padB} stroke="#2563eb" />
          <text x={X(spot) + 3} y={height - padB - 4} fontSize={10} fill="#1d4ed8">
            现价 {spot.toFixed(1)}
          </text>
        </g>
      )}
      <text x={4} y={Y(ymax) + 4} fontSize={10} fill="#64748b">
        {`+${ymax.toFixed(1)}bn`}
      </text>
      <text x={4} y={Y(-ymax) + 4} fontSize={10} fill="#64748b">
        {`-${ymax.toFixed(1)}bn`}
      </text>
      {ticks.map((t) => (
        <text key={t} x={X(t)} y={height - 6} fontSize={10} fill="#64748b" textAnchor="middle">
          {t.toFixed(0)}
        </text>
      ))}
    </svg>
  );
}
