import React from "react";

const PHOENIX_SRC = `${process.env.PUBLIC_URL || ""}/academy/phoenix-bird.png`;

/** Golden phoenix hero — image asset + glow / float animation (mockup-style). */
export default function PhoenixVisual() {
  return (
    <div className="academy-phoenix-visual" aria-hidden>
      <div className="academy-phoenix-visual__stars" />
      <div className="academy-phoenix-visual__mountains" />
      <div className="academy-phoenix-visual__glow academy-phoenix-visual__glow--core" />
      <div className="academy-phoenix-visual__glow academy-phoenix-visual__glow--halo" />

      <div className="academy-phoenix-bird-wrap">
        <img
          src={PHOENIX_SRC}
          alt=""
          className="academy-phoenix-bird"
          draggable={false}
        />
        <div className="academy-phoenix-bird-shine" />
      </div>

      <div className="academy-phoenix-visual__embers">
        {Array.from({ length: 6 }).map((_, i) => (
          <span key={i} className="academy-phoenix-ember" style={{ "--i": i }} />
        ))}
      </div>
    </div>
  );
}
