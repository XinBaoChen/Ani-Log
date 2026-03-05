"use client";

import {
  Search,
  Users,
  MapPin,
  Sword,
  Sparkles,
  Tv2,
  MonitorPlay,
  Zap,
  Database,
  ArrowUpRight,
} from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";
import SearchBar from "@/components/SearchBar";
import CharacterCard from "@/components/CharacterCard";
import CaptureControl from "@/components/CaptureControl";
import { ContainerScroll } from "@/components/ui/container-scroll-animation";
import { useSearchStore } from "@/store/useSearchStore";
import { cn } from "@/lib/utils";

// Polished app preview inside the ContainerScroll card
const AppPreview = () => {
  const fakeCharacters = [
    { name: "Levi Ackermann", seen: "342", initials: "LA", bg: "bg-blue-500/30", ring: "ring-blue-500/40", active: true },
    { name: "Mikasa Ackermann", seen: "298", initials: "MA", bg: "bg-pink-500/30", ring: "ring-pink-500/40", active: false },
    { name: "Armin Arlert", seen: "211", initials: "AA", bg: "bg-amber-500/30", ring: "ring-amber-500/40", active: false },
    { name: "Eren Yeager", seen: "401", initials: "EY", bg: "bg-emerald-500/30", ring: "ring-emerald-500/40", active: false },
    { name: "Historia Reiss", seen: "89", initials: "HR", bg: "bg-violet-500/30", ring: "ring-violet-500/40", active: false },
    { name: "Hange Zoë", seen: "176", initials: "HZ", bg: "bg-orange-500/30", ring: "ring-orange-500/40", active: false },
  ];
  const fakeScenes = [
    { label: "Castle courtyard at dusk", time: "0:18:34", color: "bg-violet-400" },
    { label: "Training grounds sequence", time: "0:04:12", color: "bg-blue-400" },
    { label: "Underground city passage", time: "0:31:08", color: "bg-cyan-400" },
  ];

  return (
    <div className="w-full h-full flex bg-[#0d0d0f] text-surface-200 overflow-hidden font-sans">

      {/* Left sidebar strip */}
      <div className="hidden md:flex flex-col items-center gap-3 w-12 flex-shrink-0 py-3 border-r border-white/[0.06] bg-white/[0.02]">
        <div className="w-6 h-6 rounded-md bg-gradient-to-br from-primary-500 to-pink-500 flex-shrink-0" />
        <div className="mt-2 flex flex-col gap-2.5">
          {[Sparkles, Search, Users, Tv2, MonitorPlay].map((Icon, i) => (
            <div key={i} className={cn(
              "w-7 h-7 rounded-lg flex items-center justify-center",
              i === 2 ? "bg-primary-500/20" : "hover:bg-white/5"
            )}>
              <Icon className={cn("w-3.5 h-3.5", i === 2 ? "text-primary-400" : "text-surface-600")} />
            </div>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Topbar */}
        <div className="flex-shrink-0 flex items-center gap-3 px-4 py-2 border-b border-white/[0.06] bg-white/[0.02]">
          <div className="flex gap-1.5 flex-shrink-0">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
          </div>
          <div className="flex items-center gap-2 flex-1 max-w-sm px-3 py-1.5 rounded-lg bg-white/[0.05] border border-white/[0.08]">
            <Search className="w-3 h-3 text-surface-500 flex-shrink-0" />
            <span className="text-[11px] text-surface-400 truncate">blue-haired swordsman with scar</span>
            <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-primary-500/20 text-primary-400 font-medium flex-shrink-0">8 hits</span>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[9px] text-emerald-400 font-medium">Live</span>
            </div>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">

          {/* Centre panel */}
          <div className="flex-1 p-3 overflow-hidden flex flex-col gap-3">

            {/* Characters */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[9px] font-semibold text-surface-500 uppercase tracking-widest">Characters</span>
                <span className="text-[9px] text-surface-600">{fakeCharacters.length} found</span>
              </div>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-1.5">
                {fakeCharacters.map((char) => (
                  <div
                    key={char.name}
                    className={cn(
                      "rounded-xl p-2 flex flex-col gap-1.5 cursor-pointer transition-all",
                      char.active
                        ? "bg-white/[0.08] ring-1 " + char.ring
                        : "bg-white/[0.03] hover:bg-white/[0.06]"
                    )}
                  >
                    <div className={cn(
                      "w-full aspect-square rounded-lg flex items-center justify-center text-white font-bold text-[10px]",
                      char.bg
                    )}>
                      {char.initials}
                    </div>
                    <p className="text-[9px] font-medium text-surface-300 leading-tight truncate">{char.name}</p>
                    <p className="text-[8px] text-surface-600">{char.seen} scenes</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Scenes */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[9px] font-semibold text-surface-500 uppercase tracking-widest">Scenes</span>
                <span className="text-[9px] text-surface-600">3 matches</span>
              </div>
              <div className="flex flex-col gap-1">
                {fakeScenes.map((scene) => (
                  <div
                    key={scene.label}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.06] transition-colors cursor-pointer"
                  >
                    <div className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", scene.color)} />
                    <span className="text-[11px] text-surface-300 flex-1 truncate">{scene.label}</span>
                    <span className="text-[10px] font-mono text-surface-600">{scene.time}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right stats panel */}
          <div className="hidden md:flex w-36 flex-col gap-1.5 p-3 border-l border-white/[0.06]">
            <p className="text-[8px] font-semibold text-surface-600 uppercase tracking-widest mb-1">Stats</p>
            {[
              { icon: Users, label: "Characters", val: "6", color: "text-primary-400", bg: "bg-primary-500/10" },
              { icon: Tv2, label: "Scenes", val: "1,240", color: "text-blue-400", bg: "bg-blue-500/10" },
              { icon: MapPin, label: "Locations", val: "87", color: "text-cyan-400", bg: "bg-cyan-500/10" },
              { icon: Sword, label: "Items", val: "43", color: "text-pink-400", bg: "bg-pink-500/10" },
            ].map(({ icon: Icon, label, val, color, bg }) => (
              <div key={label} className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-white/[0.03] border border-white/[0.05]">
                <div className={cn("w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0", bg)}>
                  <Icon className={cn("w-2.5 h-2.5", color)} />
                </div>
                <div>
                  <p className="text-[11px] font-bold text-surface-100 leading-none">{val}</p>
                  <p className="text-[8px] text-surface-600 mt-0.5">{label}</p>
                </div>
              </div>
            ))}
            <div className="mt-auto p-2 rounded-lg bg-emerald-500/8 border border-emerald-500/15">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[9px] text-emerald-400 font-semibold">Capturing</span>
              </div>
              <p className="text-[8px] text-surface-500">2 fps · Attack on Titan</p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

const features = [
  {
    size: "md:col-span-2 md:row-span-2",
    icon: MonitorPlay,
    iconColor: "text-violet-400",
    accent: "from-violet-500/10 to-transparent",
    tag: "Core engine",
    title: "Real-time screen capture",
    body: "A C++ capture engine samples your screen while you watch — no manual clipping. Smart frame diffing skips duplicates so only the moments that matter reach the pipeline.",
  },
  {
    size: "md:col-span-1",
    icon: Zap,
    iconColor: "text-amber-400",
    accent: "from-amber-500/10 to-transparent",
    tag: "Detection",
    title: "YOLO + CLIP in tandem",
    body: "YOLO-World detects objects and faces; CLIP embeds them. Multi-object tracking keeps identity consistent across cuts.",
  },
  {
    size: "md:col-span-1",
    icon: Search,
    iconColor: "text-cyan-400",
    accent: "from-cyan-500/10 to-transparent",
    tag: "Search",
    title: "Natural language queries",
    body: '"Blue-haired girl with katana" just works. Vector similarity over CLIP embeddings, no keyword matching.',
  },
  {
    size: "md:col-span-1",
    icon: Database,
    iconColor: "text-emerald-400",
    accent: "from-emerald-500/10 to-transparent",
    tag: "Storage",
    title: "Persistent character wiki",
    body: "Every tracked entity gets a page: appearances, first seen, items held, locations visited — all built automatically.",
  },
  {
    size: "md:col-span-2",
    icon: Sparkles,
    iconColor: "text-pink-400",
    accent: "from-pink-500/10 to-transparent",
    tag: "AI summary",
    title: "Story arc generation",
    body: "LLM-written story arc summaries from detected scene clusters. Know what happened in a session without rewatching.",
  },
];

export default function HomePage() {
  const { results } = useSearchStore();

  return (
    <div className="min-h-screen">

      {/* Hero — text + search, all together */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-0 text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary-500/10 border border-primary-500/20 mb-6"
        >
          <Sparkles className="w-3 h-3 text-primary-400" />
          <span className="text-xs font-medium text-primary-300 tracking-wide">
            Autonomous scene contextualizer
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="text-[2.6rem] md:text-[4.2rem] font-extrabold tracking-tight leading-[1.08] mb-5"
        >
          Your anime.
          <br />
          <span className="text-gradient">Now searchable.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-base md:text-lg text-surface-400 max-w-xl mx-auto leading-relaxed mb-8"
        >
          Ani-Log watches while you watch — building a live wiki of every
          character, location, and item without you lifting a finger.
        </motion.p>

        {/* Search bar — part of the hero, not floating below */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
          className="text-left"
        >
          <SearchBar />
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <span className="text-xs text-surface-500">Try:</span>
            {["blue-haired swordsman", "castle at sunset", "dragon fight", "school uniform"].map((q) => (
              <button
                key={q}
                className="px-2.5 py-1 rounded-lg bg-surface-800/50 text-xs text-surface-400 hover:bg-surface-700 hover:text-surface-200 transition-all border border-surface-700/50"
              >
                {q}
              </button>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Scroll-animated app preview */}
      <ContainerScroll
        titleComponent={
          <div className="flex items-center justify-center gap-2 mb-1">
            <div className="h-px w-8 bg-surface-700" />
            <span className="text-[10px] font-semibold text-surface-500 uppercase tracking-[0.15em]">App preview</span>
            <div className="h-px w-8 bg-surface-700" />
          </div>
        }
      >
        <AppPreview />
      </ContainerScroll>

      {/* Search results */}
      {results.length > 0 && (
        <section className="max-w-6xl mx-auto px-6 mb-16">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-surface-200">
              Results
              <span className="text-surface-500 ml-2 text-sm font-normal">
                {results.length} found
              </span>
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {results.map((result) => (
              <CharacterCard key={result.id} data={result} />
            ))}
          </div>
        </section>
      )}

      {/* Bento features */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-10"
        >
          <p className="text-xs text-primary-400 font-medium uppercase tracking-widest mb-2">
            Under the hood
          </p>
          <h2 className="text-3xl font-bold text-surface-50">
            Built for the obsessive watcher
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 auto-rows-[minmax(160px,auto)]">
          {features.map((feat, i) => (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className={cn(
                "relative group overflow-hidden rounded-2xl border border-surface-800 bg-surface-900/60 p-5",
                "hover:border-surface-700 transition-colors duration-200",
                feat.size
              )}
            >
              <div
                className={cn(
                  "absolute inset-0 bg-gradient-to-br opacity-60 pointer-events-none",
                  feat.accent
                )}
              />
              <div className="relative z-10 h-full flex flex-col">
                <div className="flex items-start justify-between mb-3">
                  <feat.icon className={cn("w-5 h-5", feat.iconColor)} />
                  <span className="text-[10px] font-medium text-surface-500 uppercase tracking-wider">
                    {feat.tag}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-surface-100 mb-2 leading-snug">
                  {feat.title}
                </h3>
                <p className="text-sm text-surface-400 leading-relaxed flex-1">
                  {feat.body}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="flex items-center gap-4 mt-8"
        >
          <Link
            href="/capture"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium transition-all shadow-lg shadow-primary-600/20 hover:shadow-primary-500/30 active:scale-[0.98]"
          >
            <MonitorPlay className="w-4 h-4" />
            Start capturing
          </Link>
          <Link
            href="/search"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-surface-800 hover:bg-surface-700 text-surface-200 text-sm font-medium transition-all border border-surface-700"
          >
            Browse library
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </motion.div>
      </section>

      <CaptureControl />
    </div>
  );
}
