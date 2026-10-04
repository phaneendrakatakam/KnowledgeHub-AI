# Hyperframes Composition Brief: KnowledgeHub AI V3

## Objective
Create a short, premium launch-style brag video for KnowledgeHub AI V3.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20.2 seconds

## Source Material
- Project root: `C:\Users\Phaneendra katakam\Desktop\AI FDE\01-KnowledgeHub-AI`
- Primary files read: `frontend/index.html`
- Product name: KnowledgeHub AI V3
- Tagline / strongest claim: "Your documents. Made conversational."
- Key UI or visual moment to recreate: The elegant glass translucent container UI cards with blur filter, thin colored borders, glowing drop shadows, and radial background gradient.
- Copy that must appear verbatim:
  - "Private AI Workspace"
  - "KnowledgeHub AI V3"
  - "Your documents. Made conversational."
  - "Always grounded in verified local context."
  - "No hallucinating. Just fact."
  - "Grounded in Truth. Styled in Glass."

## Creative Direction
- Tone preset: `polished`
- Creative direction: "elegant premium product film"
- Interpretation: Restraint, soft timing, clean alignments, gorgeous translucent backgrounds, slow transitions, and perfectly aligned audio.
- Angle: A showcase of visual elegance matching robust engineering. Real, grounded AI that has the confidence to retrieve supporting evidence—or decline unsupported queries—styled in a stunning modern "Aurora Glass" UI.
- Hook: A dark-themed premium fade-in of the glass-morphic login panel.
- Outro / punchline: Centerlogo presentation "Grounded in Truth. Styled in Glass."
- Avoid:
  - Generic SaaS language like "streamline your workflow"
  - Abstract non-product graphics or stock video loops
  - Flashing text, fast zoom, or erratic motion profiles

## Visual Identity
- Background: `#f3f5fb` with radial gradients `rgba(109, 93, 252, 0.10)` and `rgba(79, 124, 255, 0.08)`
- Text: `#1c2333` (Primary), `#697386` (Secondary), `#9aa3b2` (Muted)
- Accent: `#6d5dfc` (Aurora purple)
- Display font: Inter, sans-serif
- Body font: Inter, sans-serif
- Visual references from the project: Translucent panels with background blur (`backdrop-filter: blur(16px)`), stat-cards grid, "Sources & Context" sidebar panel, and the gold/purple highlighted RAG "Grounded responses" card.

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. **Scene 1: The Gateway** (0.00s - 3.27s) — Dark glass login card. Title: "KnowledgeHub AI V3" / "Private AI Workspace".
2. **Scene 2: Main Workspace** (3.27s - 8.74s) — Translucent glass dashboard. 4 stat cards slide in sequentially (beat grid: 3.82s, 4.39s, 4.91s, 5.34s). Title: "Your documents, made conversational."
3. **Scene 3: Grounded In Truth** (8.74s - 13.11s) — Main Chat panel with a user question typing in and the "Sources & Context" panel lighting up on the right. Verbatim line: "Always grounded in verified local context."
4. **Scene 4: The Power of Rejection** (13.11s - 17.47s) — User asks unsupported question, system returns a polite decline, and the Grounded Responses card highlights. Verbatim line: "No hallucinating. Just fact."
5. **Scene 5: Outro / Logo** (17.47s - 20.20s) — Premium gradient outro with the main brand logo slamming in and fading out on the final music beat. Verbatim line: "Grounded in Truth. Styled in Glass."

## Audio
- Audio role: Warm, steady, cinematic-adjacent corporate bed with precise, restrained sound effects.
- Audio arc: Begins as a sleek, professional intro, provides low-frequency transition hits on scene changes, supports dashboard card arrivals, and resolves with a deep resonant bell chime on the final logo slam.
- Music: `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (copied from skill assets)
- Music treatment: Main loop starts at 0.0s at volume 0.35, ducking under typing and actions, and fades out cleanly from 18.5s to 20.2s.
- Music cue guidance:
  - Preset path: `assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`
  - Target strong-cue locks:
    - 3.27s: Scene 1 → Scene 2 Transition (Transition hit `impactSoft_medium_001.ogg`)
    - 8.74s: Scene 2 → Scene 3 Transition (Transition hit `impactSoft_medium_001.ogg`)
    - 13.11s: Scene 3 → Scene 4 Transition (Transition hit `impactSoft_medium_001.ogg`)
    - 17.47s: Scene 4 → Scene 5 Logo Slam (Logo hit `impactBell_heavy_000.ogg`)
  - Beat-grid window for stat card pop-ins (Scene 2):
    - Stat 1: 3.82s (card-slide sound `casino/card-slide-1.ogg`)
    - Stat 2: 4.39s (card-slide sound `casino/card-slide-1.ogg`)
    - Stat 3: 4.91s (card-slide sound `casino/card-slide-1.ogg`)
    - Stat 4: 5.34s (card-slide sound `casino/card-slide-1.ogg`)
- Audio-reactive treatment: Subtle; background radial glow size/opacity should scale gracefully with the music's RMS energy (scale: 0.98 to 1.05) to keep the video dynamically alive.
- SFX selection guidance:
  - Button clicks and cursor actions use `interface/click_003.ogg`
  - Stat card arrivals use `casino/card-slide-1.ogg`
  - Scene transitions use `impact/impactSoft_medium_001.ogg`
  - Outro logo slam uses `impact/impactBell_heavy_000.ogg`
- Exact SFX choice: Copied into `brag-output/composition/assets/sfx/` and referenced relatively in HTML.

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills to create `brag-output/composition/`.

Requirements:
- Show real elements from the project's visual style (Aurora Glass translucent panels, RAG stat cards, Sources panel).
- Use native GSAP for fluid, smooth, high-quality transitions.
- All text must stay readable and fully compliant with WCAG/contrast rules.
- Set container widths and heights to 1920x1080.
- Use local assets for audio and script libraries.
- Run `hyperframes check` inside `brag-output/composition/` to validate all layout and contrast constraints before rendering.
