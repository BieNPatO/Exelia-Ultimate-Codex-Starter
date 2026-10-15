---
name: premium-motion
description: Apply when designing or implementing polished UI motion in React, including buttons, layout transitions, charts and scroll effects; use accessible, performant, purposeful animation.
---

# Premium Motion — React / Next.js

Use this skill on tasks involving animations or gesture-driven UI. Confirm the actual React/Next.js and package versions first. Pick **one primary engine per interaction**:

1. CSS `transition`, `@keyframes` or Web Animations API for simple hover, focus and loading effects.
2. Motion (`motion/react`) for stateful React enter/exit, layout changes, gestures, presence and staggered content, *only if installed and supported*.
3. GSAP/ScrollTrigger for independently justified complex timelines. Do not pull in GSAP, Lenis, or another library by default.
4. Existing visualization libraries for charts; animate only meaningful data changes and disable excessive effects in large datasets.

## Checklist

- Confirm whether animation improves affordance, hierarchy or feedback; don't animate every element.
- Define reusable motion tokens (duration, ease, spring stiffness, reduced motion) in the app's **existing** styling system instead of creating parallel systems.
- Use `transform` and `opacity` where feasible, avoid layout thrashing, large paint areas and expensive blur/filter effects on low-end devices.
- Use `prefers-reduced-motion` / Motion's reduced-motion support, visible focus and keyboard interaction; never let animation conceal errors.
- In Next.js, respect server/client component boundaries, hydration and dynamic imports.
- Verify both touch and mouse behavior; no hover-only essential actions.
- Test loading, focus, disabled, success, failure, pending, empty and cleanup states.
- For page transitions, avoid experimental React APIs without explicit compatibility verification.
- Supply measurements/recordings or browser evidence when animation behavior is central.

## Example (CSS, no runtime dependency)

```css
.interactive-button {
  transition: transform 160ms ease, box-shadow 160ms ease;
}
.interactive-button:hover { transform: translateY(-2px); }
.interactive-button:active { transform: translateY(0) scale(0.98); }
@media (prefers-reduced-motion: reduce) {
  .interactive-button { transition: none; }
}
```

Never sacrifice security, accessibility or acceptance requirements in pursuit of animation brevity (including Ponytail optimization).
