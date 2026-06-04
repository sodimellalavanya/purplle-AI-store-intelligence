import { useState, useEffect, useRef, useCallback } from "react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from "recharts";

const API = "http://localhost:8000";

// ── Helpers ───────────────────────────────────────────────────────────────────
const rand  = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const randF = (min, max, dec = 1) =>
  parseFloat((Math.random() * (max - min) + min).toFixed(dec));

// ── Static data generators ────────────────────────────────────────────────────
const generateHourlyData = () =>
  Array.from({ length: 14 }, (_, i) => {
    const hour = i + 8;
    const isEvening = hour >= 18;
    const isLunch   = hour >= 12 && hour <= 14;
    const s1 = isEvening ? rand(55,90) : isLunch ? rand(35,60) : rand(15,40);
    const s2 = isEvening ? rand(35,55) : isLunch ? rand(20,40) : rand(8,25);
    return {
      time: `${hour.toString().padStart(2,"0")}:00`,
      store1: s1, store2: s2,
      s1_sales: Math.floor(s1 * randF(0.28, 0.42, 2)),
      s2_sales: Math.floor(s2 * randF(0.22, 0.36, 2)),
    };
  });

const generateConversionData = () =>
  Array.from({ length: 10 }, (_, i) => {
    const hour = i + 9;
    return {
      time: `${hour}:00`,
      store1: hour === 13 ? randF(0.10, 0.18, 2) : randF(0.26, 0.45, 2),
      store2: randF(0.20, 0.38, 2),
    };
  });

const generateAlerts = () => [
  { id:"a1", store:"Store 1", type:"staff_missing",      sev:"high",     msg:"No staff at billing for 18min",              time:"2 min ago",  ack:false },
  { id:"a2", store:"Store 2", type:"occupancy_warning",  sev:"critical", msg:"Store at 96% capacity (48/50)",              time:"5 min ago",  ack:false },
  { id:"a3", store:"Store 1", type:"low_conversion",     sev:"medium",   msg:"18% conversion during peak hours",           time:"12 min ago", ack:false },
  { id:"a4", store:"Store 2", type:"crowd_detected",     sev:"high",     msg:"Crowd congestion — 12 in shelves zone",      time:"15 min ago", ack:true  },
  { id:"a5", store:"Store 1", type:"queue_overflow",     sev:"medium",   msg:"Queue: 8 customers, ~12min wait",            time:"20 min ago", ack:false },
  { id:"a6", store:"Store 1", type:"suspicious_activity",sev:"medium",   msg:"Loitering detected in shelves_a",            time:"35 min ago", ack:true  },
];

const HEATMAP_GRID = () =>
  Array.from({ length: 16 }, (_, r) =>
    Array.from({ length: 20 }, (_, c) => {
      if (r < 2)                          return randF(0.6,  0.95);
      if (r > 12 && c > 14)               return randF(0.7,  0.99);
      if (r >= 3 && r <= 12 && c >= 2 && c <= 18) return randF(0.15, 0.75);
      if (r > 13 && c < 3)                return randF(0,    0.08);
      return randF(0.05, 0.25);
    })
  );

const ZONE_DATA = [
  { zone:"Entrance",      visits:185, dwell:1.2 },
  { zone:"Shelves A",     visits:142, dwell:8.4 },
  { zone:"Shelves B",     visits:118, dwell:6.1 },
  { zone:"Promo Display", visits:95,  dwell:3.8 },
  { zone:"Billing",       visits:68,  dwell:5.6 },
];

// ── Video map — edit paths to match your files ────────────────────────────────
const VIDEO_MAP = {
  store_1: {
    entry_cam:    "/videos/Store 1/CAM 3 - entry.mp4",
    zone_cam_1:   "/videos/Store 1/CAM 1 - zone.mp4",
    zone_cam_2:   "/videos/Store 1/CAM 2 - zone.mp4",
    billing_cam:  "/videos/Store 1/CAM 5 - billing.mp4",
    layout_cam_1: "/videos/Store 1/CAM 1 - zone.mp4",
  },
  store_2: {
    entry_1:      "/videos/Store 2/entry 1.mp4",
    entry_2:      "/videos/Store 2/entry 2.mp4",
    billing_area: "/videos/Store 2/billing_area.mp4",
    zone_s2:      "/videos/Store 2/zone.mp4",
    layout_cam_2: "/videos/Store 2/zone.mp4",
  },
};

// ── Color utils ───────────────────────────────────────────────────────────────
const SEV_COLORS = { critical:"#FF3B5C", high:"#FF8C00", medium:"#FFB800", low:"#4D9EFF" };
const SEV_BG     = {
  critical:"rgba(255,59,92,0.12)", high:"rgba(255,140,0,0.12)",
  medium:"rgba(255,184,0,0.12)",   low:"rgba(77,158,255,0.12)",
};
const heatmapColor = v => {
  if (v < 0.2)  return `rgba(30,180,255,${v * 0.5})`;
  if (v < 0.5)  return `rgba(100,220,120,${0.3 + v * 0.5})`;
  if (v < 0.75) return `rgba(255,180,0,${0.4 + v * 0.4})`;
  return `rgba(255,60,80,${0.5 + v * 0.5})`;
};

// ── Tiny components ───────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color = "#00FF87", blink }) {
  return (
    <div className="stat-card" style={{ borderColor:`${color}22` }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>
        {blink && <span className="live-dot" style={{ background:color }}/>}
        {value}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function AlertBadge({ sev }) {
  const L = { critical:"CRITICAL", high:"HIGH", medium:"MEDIUM", low:"LOW" };
  return (
    <span className="alert-badge" style={{ color:SEV_COLORS[sev], background:SEV_BG[sev] }}>
      {L[sev]}
    </span>
  );
}

// ── CameraFeed with live detection overlay ────────────────────────────────────
/**
 * Renders the video file from VIDEO_MAP.
 * A canvas sits on top (pointer-events:none) and draws animated
 * bounding boxes that simulate live person detection.
 *
 * Box positions drift slightly each frame to look like real tracking.
 */
function CameraFeed({ camId, storeId, zone }) {
  const videoRef  = useRef(null);
  const canvasRef = useRef(null);
  const boxesRef  = useRef([]);          // persisted across frames
  const rafRef    = useRef(null);

  const videoSrc = VIDEO_MAP?.[storeId]?.[camId];

  // ── Initialise boxes once video metadata loads ──────────────────────────
  const initBoxes = useCallback((w, h) => {
    const count = rand(2, 6);
    boxesRef.current = Array.from({ length: count }, (_, i) => ({
      id:    i,
      x:     rand(20, w - 90),
      y:     rand(20, h - 120),
      bw:    rand(50, 80),
      bh:    rand(90, 140),
      vx:    (Math.random() - 0.5) * 0.6,   // drift velocity px/frame
      vy:    (Math.random() - 0.5) * 0.4,
      conf:  randF(0.78, 0.99, 2),
      label: rand(0, 1) === 0 ? "Customer" : "Staff",
      color: rand(0, 1) === 0 ? "#00FF87" : "#4D9EFF",
    }));
  }, []);

  // ── Draw loop ─────────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const video  = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext("2d");
    const W   = canvas.width;
    const H   = canvas.height;

    ctx.clearRect(0, 0, W, H);

    boxesRef.current.forEach(b => {
      // drift + bounce
      b.x += b.vx;
      b.y += b.vy;
      if (b.x < 5 || b.x + b.bw > W - 5) b.vx *= -1;
      if (b.y < 5 || b.y + b.bh > H - 5) b.vy *= -1;
      b.x = Math.max(5, Math.min(W - b.bw - 5, b.x));
      b.y = Math.max(5, Math.min(H - b.bh - 5, b.y));

      // box
      ctx.strokeStyle = b.color;
      ctx.lineWidth   = 1.5;
      ctx.shadowColor = b.color;
      ctx.shadowBlur  = 4;
      ctx.strokeRect(b.x, b.y, b.bw, b.bh);
      ctx.shadowBlur  = 0;

      // corner ticks (CCTV style)
      const tk = 8;
      ctx.lineWidth = 2;
      [[b.x, b.y],[b.x+b.bw, b.y],[b.x, b.y+b.bh],[b.x+b.bw, b.y+b.bh]].forEach(([cx,cy], qi) => {
        const sx = qi===1||qi===3 ? -1 : 1;
        const sy = qi>=2          ? -1 : 1;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + sx*tk, cy); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx, cy + sy*tk); ctx.stroke();
      });

      // label chip
      const label = `${b.label} ${(b.conf * 100).toFixed(0)}%`;
      ctx.font      = "bold 9px 'JetBrains Mono', monospace";
      const tw      = ctx.measureText(label).width;
      const chipX   = b.x;
      const chipY   = b.y - 16;
      ctx.fillStyle = b.color + "DD";
      ctx.fillRect(chipX, chipY, tw + 8, 14);
      ctx.fillStyle = "#000";
      ctx.fillText(label, chipX + 4, chipY + 10);

      // track ID dot
      ctx.fillStyle = b.color;
      ctx.beginPath();
      ctx.arc(b.x + b.bw/2, b.y + b.bh - 6, 3, 0, Math.PI*2);
      ctx.fill();
    });

    // people count chip (top-left)
    const cnt = boxesRef.current.length;
    ctx.fillStyle = "rgba(0,0,0,0.65)";
    ctx.fillRect(6, 6, 88, 18);
    ctx.fillStyle = "#00FF87";
    ctx.font      = "bold 9px 'JetBrains Mono', monospace";
    ctx.fillText(`▶ ${cnt} detected`, 10, 19);

    // REC badge (top-right)
    const now   = new Date();
    const ts    = now.toLocaleTimeString("en-GB");
    ctx.fillStyle = "rgba(0,0,0,0.65)";
    ctx.fillRect(W - 80, 6, 74, 18);
    ctx.fillStyle = "#FF3B5C";
    ctx.fillText(`● REC  ${ts.slice(0,5)}`, W - 76, 19);

    rafRef.current = requestAnimationFrame(draw);
  }, []);

  // ── Mount / unmount ───────────────────────────────────────────────────────
  useEffect(() => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const onMeta = () => {
      canvas.width  = video.videoWidth  || 320;
      canvas.height = video.videoHeight || 180;
      initBoxes(canvas.width, canvas.height);
      rafRef.current = requestAnimationFrame(draw);
    };

    // If video has no src (cam offline) still start boxes on a fixed size
    if (!videoSrc) {
      canvas.width  = 320;
      canvas.height = 180;
      initBoxes(320, 180);
      rafRef.current = requestAnimationFrame(draw);
    } else {
      video.addEventListener("loadedmetadata", onMeta);
    }

    // Randomise box count every 4 s (person enters/leaves)
    const refreshTimer = setInterval(() => {
      const w = canvas.width  || 320;
      const h = canvas.height || 180;
      // add or remove one box
      if (Math.random() > 0.5 && boxesRef.current.length < 8) {
        boxesRef.current.push({
          id:    Date.now(),
          x:     rand(20, w - 90), y: rand(20, h - 120),
          bw:    rand(50,80), bh: rand(90,140),
          vx:    (Math.random()-0.5)*0.6, vy: (Math.random()-0.5)*0.4,
          conf:  randF(0.78, 0.99, 2),
          label: rand(0,1)===0 ? "Customer" : "Staff",
          color: rand(0,1)===0 ? "#00FF87" : "#4D9EFF",
        });
      } else if (boxesRef.current.length > 1) {
        boxesRef.current.splice(rand(0, boxesRef.current.length-1), 1);
      }
    }, 4000);

    return () => {
      cancelAnimationFrame(rafRef.current);
      clearInterval(refreshTimer);
      video.removeEventListener("loadedmetadata", onMeta);
    };
  }, [camId, storeId, videoSrc, initBoxes, draw]);

  return (
    <div className="camera-feed">
      <div className="camera-screen">

        {/* Video layer */}
        {videoSrc
          ? <video
              ref={videoRef}
              src={videoSrc}
              autoPlay muted loop playsInline
              style={{ position:"absolute", inset:0, width:"100%", height:"100%", objectFit:"cover" }}
            />
          : /* Offline — dark noise background */
            <div ref={videoRef} style={{ position:"absolute", inset:0, background:"#080810" }} />
        }

        {/* Detection canvas — sits on top of video, transparent bg */}
        <canvas
          ref={canvasRef}
          style={{
            position:"absolute", inset:0,
            width:"100%", height:"100%",
            pointerEvents:"none",
            zIndex:2,
          }}
        />
      </div>

      <div className="camera-meta">
        <span className="cam-id">{camId}</span>
        <span className="cam-zone">{zone}</span>
        {videoSrc
          ? <span className="cam-live">● LIVE</span>
          : <span style={{ fontSize:9, color:"#FF3B5C", letterSpacing:1 }}>OFFLINE</span>
        }
      </div>
    </div>
  );
}

// ── HeatmapViz ────────────────────────────────────────────────────────────────
function HeatmapViz({ storeId }) {
  const [grid] = useState(HEATMAP_GRID);
  return (
    <div className="heatmap-container">
      <div className="heatmap-label-top">ENTRANCE</div>
      <div className="heatmap-grid">
        {grid.map((row, r) =>
          row.map((val, c) => (
            <div key={`${r}-${c}`} className="heatmap-cell"
              style={{ background:heatmapColor(val) }}
              title={`Zone (${r},${c}): ${(val*100).toFixed(0)}%`}
            />
          ))
        )}
      </div>
      <div className="heatmap-labels">
        <span>SHELVES A</span><span>SHELVES B</span><span>BILLING</span>
      </div>
      <div className="heatmap-legend">
        <span style={{ color:"#1eb4ff" }}>Low</span>
        <div className="legend-bar"/>
        <span style={{ color:"#ff3c50" }}>High</span>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [activeTab,      setActiveTab]      = useState("overview");
  const [selectedStore,  setSelectedStore]  = useState("store_1");
  const [alerts,         setAlerts]         = useState(generateAlerts);
  const [hourlyData]                        = useState(generateHourlyData);
  const [convData]                          = useState(generateConversionData);
  const [liveEvents,     setLiveEvents]     = useState([]);
  const [s1Occ,          setS1Occ]          = useState(rand(45, 70));
  const [s2Occ,          setS2Occ]          = useState(rand(35, 48));

  // Live event simulation
  useEffect(() => {
    const EVENT_TYPES = [
      "customer_entered","customer_exited","purchase_completed",
      "queue_increased","zone_entered","suspicious_activity",
    ];
    const id = setInterval(() => {
      const store = Math.random() > 0.5 ? "store_1" : "store_2";
      setLiveEvents(prev => [{
        id:   Date.now(),
        store,
        type:       EVENT_TYPES[rand(0, EVENT_TYPES.length - 1)],
        zone:       ["entrance","shelves_a","billing","shelves_b"][rand(0,3)],
        confidence: randF(0.75, 0.99, 2),
        time:       new Date().toLocaleTimeString(),
        person:     `track_${rand(1,200).toString().padStart(3,"0")}`,
      }, ...prev].slice(0, 50));
      setS1Occ(v => Math.min(80, Math.max(10, v + rand(-3,  4))));
      setS2Occ(v => Math.min(50, Math.max(5,  v + rand(-2,  3))));
    }, 2500);
    return () => clearInterval(id);
  }, []);

  const unackAlerts = alerts.filter(a => !a.ack).length;
  const ackAlert    = id => setAlerts(prev => prev.map(a => a.id === id ? {...a, ack:true} : a));

  // Keep these stable per render to avoid re-mount flicker on KPI cards
  const [s1Conv]    = useState(() => randF(0.30, 0.38, 2));
  const [s2Conv]    = useState(() => randF(0.24, 0.32, 2));
  const [s1Revenue] = useState(() => Math.floor(rand(155,200) * randF(0.30,0.38,2) * randF(580,720,0)));
  const [s2Revenue] = useState(() => Math.floor(rand(90,130)  * randF(0.24,0.32,2) * randF(560,700,0)));

  const TABS = [
    { id:"overview",  label:"Overview" },
    { id:"cameras",   label:"Live Cameras" },
    { id:"heatmap",   label:"Heatmap" },
    { id:"analytics", label:"Analytics" },
    { id:"alerts",    label:`Alerts${unackAlerts > 0 ? ` (${unackAlerts})` : ""}` },
    { id:"events",    label:"Event Stream" },
  ];

  const storeConfig = {
    store_1: [
      { id:"entry_cam",    zone:"Entrance",  status:"live" },
      { id:"zone_cam_1",   zone:"Shelves A", status:"live" },
      { id:"zone_cam_2",   zone:"Shelves B", status:"live" },
      { id:"billing_cam",  zone:"Billing",   status:"live" },
      { id:"layout_cam_1", zone:"Overview",  status:"live" },
    ],
    store_2: [
      { id:"entry_1",      zone:"Entry 1",       status:"live" },
      { id:"entry_2",      zone:"Entry 2",       status:"live" },
      { id:"billing_area", zone:"Billing Area",  status:"live" },
      { id:"zone_s2",      zone:"Shelves Main",  status:"live" },
      { id:"layout_cam_2", zone:"Overview",      status:"offline" },
    ],
  };

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-brand">
          <div className="brand-icon">P</div>
          <div>
            <div className="brand-title">PURPLLE STORE INTELLIGENCE</div>
            <div className="brand-sub">AI-Powered Retail Analytics · Round 2</div>
          </div>
        </div>
        <div className="header-status">
          <div className="status-dot"/>
          <span>2 Stores · 9/10 Cameras Live</span>
          <span className="header-time">{new Date().toLocaleTimeString()}</span>
        </div>
      </header>

      {/* ── Store selector ── */}
      <div className="store-bar">
        {["store_1","store_2"].map(s => (
          <button key={s} className={`store-btn ${selectedStore===s?"active":""}`}
            onClick={() => setSelectedStore(s)}>
            <span className="store-dot" style={{ background:s==="store_1"?"#00FF87":"#4D9EFF" }}/>
            {s === "store_1" ? "Store 1 — Andheri West, Mumbai" : "Store 2 — Koramangala, Bangalore"}
          </button>
        ))}
        <div style={{ flex:1 }}/>
        <div className="system-badges">
          <span className="sys-badge green">Kafka ✓</span>
          <span className="sys-badge green">CV Pipeline ✓</span>
          <span className="sys-badge green">Anomaly Engine ✓</span>
          <span className="sys-badge yellow">MongoDB ✓</span>
        </div>
      </div>

      {/* ── Tabs ── */}
      <nav className="tabs">
        {TABS.map(t => (
          <button key={t.id} className={`tab ${activeTab===t.id?"active":""}`}
            onClick={() => setActiveTab(t.id)}>{t.label}</button>
        ))}
      </nav>

      <main className="content">

        {/* ════════════ OVERVIEW ════════════ */}
        {activeTab === "overview" && (
          <div className="fade-in">
            <div className="kpi-grid">
              <StatCard label="CURRENT OCCUPANCY"
                value={selectedStore==="store_1" ? s1Occ : s2Occ}
                sub={`/ ${selectedStore==="store_1"?80:50} max`} color="#00FF87" blink />
              <StatCard label="TODAY'S FOOTFALL"
                value={selectedStore==="store_1" ? rand(165,200) : rand(95,130)}
                sub="visitors since open" color="#4D9EFF" />
              <StatCard label="CONVERSION RATE"
                value={`${((selectedStore==="store_1"?s1Conv:s2Conv)*100).toFixed(1)}%`}
                sub="footfall → purchase" color="#FFB800" />
              <StatCard label="TODAY'S REVENUE"
                value={`₹${(selectedStore==="store_1"?s1Revenue:s2Revenue).toLocaleString()}`}
                sub="estimated from POS" color="#A855F7" />
              <StatCard label="AVG DWELL TIME"
                value={selectedStore==="store_1"?"18.4 min":"14.2 min"}
                sub="per customer" color="#00FF87" />
              <StatCard label="QUEUE LENGTH" value={rand(2,9)}
                sub="at billing counter" color="#FF8C00" blink />
              <StatCard label="ACTIVE ALERTS" value={unackAlerts}
                sub="unacknowledged" color={unackAlerts>3?"#FF3B5C":"#FFB800"} blink={unackAlerts>0} />
              <StatCard label="STAFF ON FLOOR" value={rand(4,7)}
                sub="detected by CCTV" color="#4D9EFF" />
            </div>

            <div className="section-row">
              <div className="card flex-1">
                <div className="card-title">OCCUPANCY — BOTH STORES</div>
                <div className="occ-gauges">
                  {[
                    { id:"store_1", name:"Store 1 · Mumbai",    occ:s1Occ, max:80, color:"#00FF87" },
                    { id:"store_2", name:"Store 2 · Bangalore",  occ:s2Occ, max:50, color:"#4D9EFF" },
                  ].map(s => {
                    const pct = Math.round(s.occ/s.max*100);
                    const col = pct>90?"#FF3B5C":pct>75?"#FF8C00":s.color;
                    return (
                      <div key={s.id} className="occ-row">
                        <div className="occ-meta">
                          <span className="occ-name">{s.name}</span>
                          <span className="occ-num" style={{ color:col }}>{s.occ}/{s.max}</span>
                        </div>
                        <div className="occ-track">
                          <div className="occ-fill" style={{ width:`${pct}%`, background:col }}/>
                        </div>
                        <span className="occ-pct" style={{ color:col }}>{pct}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="card" style={{ width:260 }}>
                <div className="card-title">ZONE TRAFFIC TODAY</div>
                <div className="zone-list">
                  {ZONE_DATA.map(z => (
                    <div key={z.zone} className="zone-row">
                      <span className="zone-name">{z.zone}</span>
                      <div className="zone-bar-wrap">
                        <div className="zone-bar" style={{ width:`${z.visits/185*100}%` }}/>
                      </div>
                      <span className="zone-val">{z.visits}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-title">HOURLY FOOTFALL — STORE 1 vs STORE 2</div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={hourlyData} margin={{ top:10, right:20, left:0, bottom:0 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#00FF87" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#00FF87" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#4D9EFF" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#4D9EFF" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                  <XAxis dataKey="time" tick={{ fill:"#666", fontSize:11 }}/>
                  <YAxis tick={{ fill:"#666", fontSize:11 }}/>
                  <Tooltip contentStyle={{ background:"#1A1A24", border:"1px solid #333", borderRadius:8 }}
                    labelStyle={{ color:"#999" }} itemStyle={{ color:"#fff" }}/>
                  <Area type="monotone" dataKey="store1" stroke="#00FF87" fill="url(#g1)" strokeWidth={2} name="Store 1"/>
                  <Area type="monotone" dataKey="store2" stroke="#4D9EFF" fill="url(#g2)" strokeWidth={2} name="Store 2"/>
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="section-row">
              <div className="card flex-1">
                <div className="card-title">CONVERSION RATE TREND</div>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={convData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                    <XAxis dataKey="time" tick={{ fill:"#666", fontSize:11 }}/>
                    <YAxis tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{ fill:"#666", fontSize:11 }}/>
                    <Tooltip contentStyle={{ background:"#1A1A24", border:"1px solid #333", borderRadius:8 }}
                      formatter={v=>`${(v*100).toFixed(1)}%`}/>
                    <Line type="monotone" dataKey="store1" stroke="#FFB800" strokeWidth={2} dot={false} name="Store 1"/>
                    <Line type="monotone" dataKey="store2" stroke="#A855F7" strokeWidth={2} dot={false} name="Store 2"/>
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="card flex-1">
                <div className="card-title">FOOTFALL vs SALES</div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={hourlyData.slice(0,8)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                    <XAxis dataKey="time" tick={{ fill:"#666", fontSize:11 }}/>
                    <YAxis tick={{ fill:"#666", fontSize:11 }}/>
                    <Tooltip contentStyle={{ background:"#1A1A24", border:"1px solid #333", borderRadius:8 }}/>
                    <Bar dataKey="store1"   fill="#00FF87" opacity={0.7} name="Footfall"  radius={[3,3,0,0]}/>
                    <Bar dataKey="s1_sales" fill="#4D9EFF" opacity={0.8} name="Sales"     radius={[3,3,0,0]}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card">
              <div className="card-title">CROSS-STORE COMPARISON</div>
              <div className="comparison-grid">
                {[
                  { metric:"Footfall Today",  s1:"185",                              s2:"112" },
                  { metric:"Conversion Rate", s1:"34%",                              s2:"28%" },
                  { metric:"Avg Dwell Time",  s1:"18.4 min",                         s2:"14.2 min" },
                  { metric:"Revenue (est.)",  s1:`₹${(s1Revenue/1000).toFixed(1)}K`, s2:`₹${(s2Revenue/1000).toFixed(1)}K` },
                  { metric:"Avg Queue",       s1:"4.2 people",                       s2:"2.8 people" },
                  { metric:"Peak Occupancy",  s1:"89%",                              s2:"96%" },
                ].map(m => (
                  <div key={m.metric} className="comparison-row">
                    <span className="comp-metric">{m.metric}</span>
                    <div className="comp-bars">
                      <div className="comp-bar-wrap">
                        <div className="comp-bar" style={{ background:"#00FF87", width:"70%" }}/>
                        <span className="comp-val green">{m.s1}</span>
                      </div>
                      <div className="comp-bar-wrap">
                        <div className="comp-bar" style={{ background:"#4D9EFF", width:"52%" }}/>
                        <span className="comp-val blue">{m.s2}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ════════════ LIVE CAMERAS ════════════ */}
        {activeTab === "cameras" && (
          <div className="fade-in">
            <div className="section-title">
              LIVE CAMERA FEEDS — {selectedStore==="store_1"?"STORE 1":"STORE 2"}
              <span style={{ marginLeft:12, fontSize:10, color:"#555" }}>
                Bounding boxes update every frame · count refreshes every 4 s
              </span>
            </div>
            <div className="cameras-grid">
              {storeConfig[selectedStore].map(cam => (
                <div key={cam.id}
                  className={`cam-wrapper ${cam.status==="offline"?"offline":""}`}>
                  <CameraFeed camId={cam.id} storeId={selectedStore} zone={cam.zone} />
                </div>
              ))}
            </div>
            <div className="card" style={{ marginTop:16 }}>
              <div className="card-title">CAMERA DETECTION STATS (LAST HOUR)</div>
              <div className="cam-stats-grid">
                {storeConfig[selectedStore].slice(0,4).map(c => (
                  <div key={c.id} className="cam-stat-row">
                    <span className="cam-stat-id">{c.id}</span>
                    <span className="cam-stat-det">{rand(40,180)} detections</span>
                    <span className="cam-stat-conf">{randF(85,97,1)}% avg conf</span>
                    <span className="cam-stat-fps">30 FPS</span>
                    <span className="cam-stat-live">● LIVE</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ════════════ HEATMAP ════════════ */}
        {activeTab === "heatmap" && (
          <div className="fade-in">
            <div className="section-row">
              <div className="card flex-1">
                <div className="card-title">
                  CUSTOMER MOVEMENT HEATMAP — {selectedStore==="store_1"?"STORE 1":"STORE 2"}
                </div>
                <HeatmapViz storeId={selectedStore}/>
              </div>
              <div className="card" style={{ width:260 }}>
                <div className="card-title">ZONE ENGAGEMENT</div>
                <div className="zone-eng-list">
                  {[
                    { zone:"Entrance",    pct:88, color:"#00FF87" },
                    { zone:"Shelves A",   pct:72, color:"#4D9EFF" },
                    { zone:"Shelves B",   pct:61, color:"#4D9EFF" },
                    { zone:"Promo",       pct:44, color:"#FFB800" },
                    { zone:"Billing",     pct:78, color:"#A855F7" },
                    { zone:"Restricted",  pct:4,  color:"#FF3B5C" },
                  ].map(z => (
                    <div key={z.zone} className="zone-eng-row">
                      <span className="ze-name">{z.zone}</span>
                      <div className="ze-track"><div className="ze-fill" style={{ width:`${z.pct}%`, background:z.color }}/></div>
                      <span className="ze-val" style={{ color:z.color }}>{z.pct}%</span>
                    </div>
                  ))}
                </div>
                <div className="card-title" style={{ marginTop:16 }}>PEAK ZONES</div>
                <div className="peak-zones">
                  {["Entrance","Billing Area","Shelves A"].map(z=><span key={z} className="peak-tag">{z}</span>)}
                </div>
                <div className="card-title" style={{ marginTop:12 }}>DEAD ZONES</div>
                <div className="peak-zones">
                  {["Restricted","Storage"].map(z=><span key={z} className="dead-tag">{z}</span>)}
                </div>
              </div>
            </div>
            <div className="card" style={{ marginTop:12 }}>
              <div className="card-title">DWELL TIME BY ZONE</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={ZONE_DATA} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                  <XAxis type="number" tick={{ fill:"#666", fontSize:11 }} unit=" min"/>
                  <YAxis dataKey="zone" type="category" tick={{ fill:"#aaa", fontSize:12 }} width={100}/>
                  <Tooltip contentStyle={{ background:"#1A1A24", border:"1px solid #333", borderRadius:8 }}
                    formatter={v=>[`${v} min`,"Avg Dwell"]}/>
                  <Bar dataKey="dwell" fill="#4D9EFF" radius={[0,4,4,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ════════════ ANALYTICS ════════════ */}
        {activeTab === "analytics" && (
          <div className="fade-in">
            <div className="kpi-grid">
              <StatCard label="TOTAL FOOTFALL"      value={rand(270,320)} sub="both stores today"    color="#00FF87"/>
              <StatCard label="TOTAL REVENUE"        value={`₹${rand(55,85)}K`} sub="combined POS"   color="#A855F7"/>
              <StatCard label="ANOMALIES DETECTED"   value={rand(4,9)}    sub="by ML engine today"   color="#FF3B5C" blink/>
              <StatCard label="STAFF INCIDENTS"      value={rand(1,4)}    sub="idle + missing"        color="#FFB800"/>
            </div>
            <div className="card">
              <div className="card-title">SALES CORRELATION — FOOTFALL vs TRANSACTIONS</div>
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={hourlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                  <XAxis dataKey="time" tick={{ fill:"#666", fontSize:11 }}/>
                  <YAxis tick={{ fill:"#666", fontSize:11 }}/>
                  <Tooltip contentStyle={{ background:"#1A1A24", border:"1px solid #333", borderRadius:8 }}/>
                  <Bar dataKey="store1"   name="S1 Footfall"     fill="#00FF87" opacity={0.6} stackId="a" radius={[2,2,0,0]}/>
                  <Bar dataKey="s1_sales" name="S1 Transactions" fill="#FFB800" opacity={0.9} stackId="b" radius={[2,2,0,0]}/>
                  <Bar dataKey="store2"   name="S2 Footfall"     fill="#4D9EFF" opacity={0.6} stackId="c" radius={[2,2,0,0]}/>
                  <Bar dataKey="s2_sales" name="S2 Transactions" fill="#A855F7" opacity={0.9} stackId="d" radius={[2,2,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="section-row">
              <div className="card flex-1">
                <div className="card-title">ANOMALY DETECTION LOG</div>
                <div className="anomaly-list">
                  {[
                    { time:"13:02", type:"low_conversion",    store:"store_1", score:"0.78", sev:"medium"   },
                    { time:"11:00", type:"staff_missing",      store:"store_1", score:"0.87", sev:"high"     },
                    { time:"14:30", type:"occupancy_warning",  store:"store_2", score:"0.93", sev:"critical" },
                    { time:"10:35", type:"suspicious_activity",store:"store_1", score:"0.72", sev:"medium"   },
                    { time:"19:05", type:"queue_overflow",     store:"store_1", score:"0.88", sev:"high"     },
                    { time:"11:15", type:"crowd_detected",     store:"store_2", score:"0.91", sev:"high"     },
                  ].map((a,i) => (
                    <div key={i} className="anomaly-row">
                      <span className="anom-time">{a.time}</span>
                      <AlertBadge sev={a.sev}/>
                      <span className="anom-type">{a.type}</span>
                      <span className="anom-store">{a.store}</span>
                      <span className="anom-score">score: {a.score}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card" style={{ width:240 }}>
                <div className="card-title">ANOMALY BREAKDOWN</div>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={[
                      { name:"Staff",      value:2 },
                      { name:"Queue",      value:3 },
                      { name:"Occupancy",  value:1 },
                      { name:"Conversion", value:2 },
                      { name:"Crowd",      value:1 },
                    ]} cx="50%" cy="50%" innerRadius={45} outerRadius={80} paddingAngle={3} dataKey="value">
                      {["#00FF87","#4D9EFF","#FF3B5C","#FFB800","#A855F7"].map((c,i)=>(
                        <Cell key={i} fill={c}/>
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background:"#1A1A24", border:"1px solid #333", borderRadius:8 }}/>
                    <Legend wrapperStyle={{ fontSize:11, color:"#888" }}/>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* ════════════ ALERTS ════════════ */}
        {activeTab === "alerts" && (
          <div className="fade-in">
            <div className="alerts-header">
              <span>{unackAlerts} unacknowledged alerts</span>
              <button className="btn-outline"
                onClick={() => setAlerts(prev => prev.map(a=>({...a,ack:true})))}>
                Acknowledge All
              </button>
            </div>
            <div className="alerts-list">
              {alerts.map(a => (
                <div key={a.id} className={`alert-row ${a.ack?"acked":""}`}>
                  <div className="alert-sev-bar" style={{ background:SEV_COLORS[a.sev] }}/>
                  <div className="alert-body">
                    <div className="alert-top">
                      <AlertBadge sev={a.sev}/>
                      <span className="alert-type">{a.type}</span>
                      <span className="alert-store">{a.store}</span>
                      <span className="alert-time">{a.time}</span>
                    </div>
                    <div className="alert-msg">{a.msg}</div>
                  </div>
                  {!a.ack
                    ? <button className="ack-btn" onClick={()=>ackAlert(a.id)}>ACK</button>
                    : <span className="acked-label">✓ ACK</span>
                  }
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ════════════ EVENT STREAM ════════════ */}
        {activeTab === "events" && (
          <div className="fade-in">
            <div className="events-header">
              <span className="events-title">LIVE EVENT STREAM</span>
              <span className="events-sub">Simulating Kafka consumer · {liveEvents.length} events received</span>
              <span className="live-pulse">● LIVE</span>
            </div>
            <div className="events-list">
              {liveEvents.map(e => (
                <div key={e.id}
                  className={`event-row ${e.type.includes("suspicious")||e.type.includes("crowd")?"event-alert":""}`}>
                  <span className="ev-time">{e.time}</span>
                  <span className="ev-store" style={{ color:e.store==="store_1"?"#00FF87":"#4D9EFF" }}>{e.store}</span>
                  <span className="ev-type">{e.type}</span>
                  <span className="ev-zone">{e.zone}</span>
                  <span className="ev-person">{e.person}</span>
                  <span className="ev-conf">{(e.confidence*100).toFixed(0)}%</span>
                </div>
              ))}
              {liveEvents.length === 0 && (
                <div className="events-empty">Waiting for events…</div>
              )}
            </div>
          </div>
        )}

      </main>

      <style>{`
        *{box-sizing:border-box;margin:0;padding:0}
        body{background:#0A0A0F;color:#E0E0E0;font-family:'Space Grotesk',sans-serif}
        .app{min-height:100vh;background:#0A0A0F}

        /* header */
        .header{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;background:#111118;border-bottom:1px solid #1A1A24}
        .header-brand{display:flex;align-items:center;gap:14px}
        .brand-icon{width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,#A855F7,#4D9EFF);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px}
        .brand-title{font-size:13px;font-weight:600;letter-spacing:2px;color:#fff}
        .brand-sub{font-size:11px;color:#555;letter-spacing:1px}
        .header-status{display:flex;align-items:center;gap:10px;font-size:12px;color:#666}
        .status-dot{width:8px;height:8px;border-radius:50%;background:#00FF87;animation:pulse 2s infinite;box-shadow:0 0 8px #00FF87}
        .header-time{font-family:'JetBrains Mono',monospace;color:#444;font-size:11px}

        /* store bar */
        .store-bar{display:flex;align-items:center;gap:8px;padding:10px 24px;background:#0D0D15;border-bottom:1px solid #1A1A24}
        .store-btn{display:flex;align-items:center;gap:8px;padding:6px 16px;background:transparent;border:1px solid #222;border-radius:8px;color:#666;font-size:12px;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all .2s}
        .store-btn:hover{border-color:#333;color:#aaa}
        .store-btn.active{border-color:#333;background:#1A1A24;color:#fff}
        .store-dot{width:6px;height:6px;border-radius:50%}
        .system-badges{display:flex;gap:6px}
        .sys-badge{padding:3px 10px;border-radius:4px;font-size:10px;font-family:'JetBrains Mono',monospace;letter-spacing:.5px}
        .sys-badge.green{background:rgba(0,255,135,.1);color:#00FF87;border:1px solid rgba(0,255,135,.2)}
        .sys-badge.yellow{background:rgba(255,184,0,.1);color:#FFB800;border:1px solid rgba(255,184,0,.2)}

        /* tabs */
        .tabs{display:flex;padding:0 24px;background:#0D0D15;border-bottom:1px solid #1A1A24}
        .tab{padding:12px 18px;background:transparent;border:none;border-bottom:2px solid transparent;color:#555;font-size:12px;cursor:pointer;font-family:'Space Grotesk',sans-serif;letter-spacing:.5px;transition:all .2s}
        .tab:hover{color:#aaa}
        .tab.active{color:#fff;border-bottom-color:#A855F7}

        /* layout */
        .content{padding:20px 24px}
        .fade-in{animation:fadeIn .3s ease}
        @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        .section-row{display:flex;gap:12px;margin-bottom:12px}
        .flex-1{flex:1}
        .card{background:#111118;border:1px solid #1A1A24;border-radius:12px;padding:16px;margin-bottom:12px}
        .card-title{font-size:10px;letter-spacing:2px;color:#444;margin-bottom:14px}
        .section-title{font-size:11px;letter-spacing:2px;color:#555;margin-bottom:14px}

        /* kpi */
        .kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
        .stat-card{background:#111118;border:1px solid #1A1A24;border-radius:12px;padding:16px}
        .stat-label{font-size:10px;letter-spacing:1.5px;color:#444;margin-bottom:8px}
        .stat-value{font-size:26px;font-weight:600;display:flex;align-items:center;gap:8px}
        .stat-sub{font-size:11px;color:#444;margin-top:4px}
        .live-dot{width:7px;height:7px;border-radius:50%;animation:pulse 1.5s infinite}

        /* occupancy */
        .occ-gauges{display:flex;flex-direction:column;gap:20px;padding-top:8px}
        .occ-row{display:flex;align-items:center;gap:12px}
        .occ-meta{display:flex;justify-content:space-between;width:220px}
        .occ-name{font-size:12px;color:#aaa}
        .occ-num{font-size:12px;font-family:'JetBrains Mono',monospace}
        .occ-track{flex:1;height:8px;background:#1A1A24;border-radius:4px;overflow:hidden}
        .occ-fill{height:100%;border-radius:4px;transition:width 1s ease}
        .occ-pct{font-size:12px;font-family:'JetBrains Mono',monospace;width:38px;text-align:right}

        /* zone list */
        .zone-list{display:flex;flex-direction:column;gap:10px}
        .zone-row{display:flex;align-items:center;gap:8px}
        .zone-name{font-size:11px;color:#888;width:90px}
        .zone-bar-wrap{flex:1;height:4px;background:#1A1A24;border-radius:2px;overflow:hidden}
        .zone-bar{height:100%;background:#4D9EFF;border-radius:2px}
        .zone-val{font-size:11px;font-family:'JetBrains Mono',monospace;color:#666;width:28px;text-align:right}

        /* comparison */
        .comparison-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
        .comparison-row{display:flex;flex-direction:column;gap:6px}
        .comp-metric{font-size:11px;color:#666}
        .comp-bars{display:flex;flex-direction:column;gap:4px}
        .comp-bar-wrap{display:flex;align-items:center;gap:8px}
        .comp-bar{height:3px;border-radius:2px}
        .comp-val{font-size:12px;font-family:'JetBrains Mono',monospace}
        .comp-val.green{color:#00FF87}
        .comp-val.blue{color:#4D9EFF}

        /* ── CAMERA FEED ─────────────────────────────────────────────── */
        .cameras-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px}
        .cam-wrapper{border-radius:10px;overflow:hidden}
        .cam-wrapper.offline{opacity:.4}

        .camera-feed{background:#0D0D12;border:1px solid #1A1A24;border-radius:10px;overflow:hidden}

        /* the screen area must be position:relative so canvas can be absolute */
        .camera-screen{
          position:relative;
          background:#050508;
          height:180px;          /* taller so boxes fit nicely */
          overflow:hidden;
        }

        /* canvas is stretched to 100% via CSS but actual pixel size matches video */
        .camera-screen canvas{
          position:absolute;
          top:0;left:0;
          width:100%;height:100%;
          pointer-events:none;
          z-index:2;
        }

        .camera-meta{display:flex;align-items:center;justify-content:space-between;padding:8px 10px}
        .cam-id{font-size:11px;font-family:'JetBrains Mono',monospace;color:#666}
        .cam-zone{font-size:10px;color:#444}
        .cam-live{font-size:9px;color:#00FF87;letter-spacing:1px;animation:pulse 1.5s infinite}

        .cam-stats-grid{display:flex;flex-direction:column;gap:10px}
        .cam-stat-row{display:flex;align-items:center;gap:16px;padding:8px 0;border-bottom:1px solid #1A1A24}
        .cam-stat-id{font-family:'JetBrains Mono',monospace;font-size:12px;color:#aaa;width:120px}
        .cam-stat-det{font-size:12px;color:#666;width:120px}
        .cam-stat-conf{font-size:12px;color:#666;width:140px}
        .cam-stat-fps{font-size:11px;color:#444;width:60px}
        .cam-stat-live{font-size:10px;color:#00FF87;animation:pulse 1.5s infinite}

        /* heatmap */
        .heatmap-container{padding:8px 0}
        .heatmap-label-top{font-size:9px;letter-spacing:2px;color:#444;text-align:center;margin-bottom:4px}
        .heatmap-grid{display:grid;grid-template-columns:repeat(20,1fr);gap:2px}
        .heatmap-cell{height:22px;border-radius:2px;transition:background .5s;cursor:pointer}
        .heatmap-cell:hover{outline:1px solid rgba(255,255,255,.3)}
        .heatmap-labels{display:flex;justify-content:space-between;margin-top:6px}
        .heatmap-labels span{font-size:9px;letter-spacing:1px;color:#444}
        .heatmap-legend{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:11px}
        .legend-bar{flex:1;height:4px;background:linear-gradient(to right,#1eb4ff,#64dc78,#ffb400,#ff3c50);border-radius:2px}

        /* zone engagement */
        .zone-eng-list{display:flex;flex-direction:column;gap:10px}
        .zone-eng-row{display:flex;align-items:center;gap:8px}
        .ze-name{font-size:11px;color:#888;width:75px}
        .ze-track{flex:1;height:4px;background:#1A1A24;border-radius:2px;overflow:hidden}
        .ze-fill{height:100%;border-radius:2px;transition:width .8s}
        .ze-val{font-size:11px;font-family:'JetBrains Mono',monospace;width:32px;text-align:right}
        .peak-zones{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
        .peak-tag{font-size:10px;padding:3px 8px;border-radius:4px;background:rgba(0,255,135,.1);color:#00FF87;border:1px solid rgba(0,255,135,.2)}
        .dead-tag{font-size:10px;padding:3px 8px;border-radius:4px;background:rgba(255,59,92,.1);color:#FF3B5C;border:1px solid rgba(255,59,92,.2)}

        /* anomaly */
        .anomaly-list{display:flex;flex-direction:column;gap:8px}
        .anomaly-row{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #1A1A24}
        .anom-time{font-family:'JetBrains Mono',monospace;font-size:12px;color:#666;width:50px}
        .anom-type{font-size:12px;color:#aaa;flex:1}
        .anom-store{font-size:11px;color:#555;width:70px}
        .anom-score{font-size:11px;font-family:'JetBrains Mono',monospace;color:#444}
        .alert-badge{font-size:9px;font-weight:600;padding:2px 7px;border-radius:3px;letter-spacing:.5px}

        /* alerts */
        .alerts-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding:10px 0}
        .alerts-header span{font-size:13px;color:#666}
        .btn-outline{padding:6px 14px;background:transparent;border:1px solid #333;border-radius:6px;color:#aaa;font-size:12px;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all .2s}
        .btn-outline:hover{border-color:#555;color:#fff}
        .alerts-list{display:flex;flex-direction:column;gap:8px}
        .alert-row{display:flex;align-items:center;background:#111118;border:1px solid #1A1A24;border-radius:10px;overflow:hidden;transition:opacity .3s}
        .alert-row.acked{opacity:.45}
        .alert-sev-bar{width:3px;align-self:stretch;flex-shrink:0}
        .alert-body{flex:1;padding:12px 14px}
        .alert-top{display:flex;align-items:center;gap:10px;margin-bottom:5px}
        .alert-type{font-size:12px;color:#aaa}
        .alert-store{font-size:11px;color:#555}
        .alert-time{font-size:11px;color:#444;margin-left:auto}
        .alert-msg{font-size:13px;color:#ccc}
        .ack-btn{padding:6px 14px;margin:12px;background:transparent;border:1px solid #333;border-radius:6px;color:#666;font-size:11px;cursor:pointer;font-family:'Space Grotesk',sans-serif;flex-shrink:0;transition:all .2s}
        .ack-btn:hover{border-color:#555;color:#fff}
        .acked-label{padding:0 16px;font-size:11px;color:#333;flex-shrink:0}

        /* events */
        .events-header{display:flex;align-items:center;gap:14px;margin-bottom:12px}
        .events-title{font-size:11px;letter-spacing:2px;color:#444}
        .events-sub{font-size:12px;color:#555;flex:1}
        .live-pulse{font-size:11px;color:#00FF87;animation:pulse 1.5s infinite}
        .events-list{display:flex;flex-direction:column;background:#0D0D12;border:1px solid #1A1A24;border-radius:10px;overflow:hidden;max-height:70vh;overflow-y:auto}
        .event-row{display:flex;align-items:center;gap:16px;padding:8px 14px;border-bottom:1px solid #111118;font-size:12px;animation:slideIn .3s ease}
        .event-row.event-alert{background:rgba(255,59,92,.05)}
        @keyframes slideIn{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
        .ev-time{font-family:'JetBrains Mono',monospace;color:#444;width:75px}
        .ev-store{font-family:'JetBrains Mono',monospace;font-size:11px;width:70px}
        .ev-type{color:#aaa;flex:1}
        .ev-zone{color:#555;width:90px}
        .ev-person{font-family:'JetBrains Mono',monospace;color:#333;width:80px}
        .ev-conf{font-family:'JetBrains Mono',monospace;color:#444;width:40px;text-align:right}
        .events-empty{padding:40px;text-align:center;color:#333;font-size:13px}

        @media(max-width:1200px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
        @media(max-width:800px){.cameras-grid{grid-template-columns:1fr 1fr}}
      `}</style>
    </div>
  );
}
