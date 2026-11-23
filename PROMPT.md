# Rebuild it for your own story

Paste this into Claude Code, opened in a clone of this repo. Fill in the three lines in brackets first.

---

I want my own version of this site: a one-screen, scroll-driven title sequence where people turn to the camera one
scroll at a time, with a place running through them as a double exposure. Use this repo as the base: keep
`index.html`'s engine (WebGL double exposure, scroll-scrubbed turn, police-light cut, preloader, tall phone layout,
finale) and change the story, the people, the places and the colours.

- **My story:** [what the site is for, e.g. "a countdown to my band's album", "the launch of our café in Lisbon"]
- **The people (3–6):** [who they are, e.g. "a fisherman, a tram driver, a pastry chef, a surfer"]
- **The place and the hours:** [e.g. "Lisbon, from 6 am to midnight"]

Work in this order and show me each result before the next step:

1. **Art direction.** Propose a palette (sky gradient + one accent for the big letters), the big background word or
   number instead of "VI", the slogan lines (three short lines per person that tell the story in order) and the
   place/time line for each person. Keep type white on a saturated sky, like the original.
2. **Start frames.** For each person, write an image prompt for a photoreal portrait in strict side profile facing
   right, head and shoulders, on a plain pale hazy sky. Same camera height and head size for everyone. For each hour,
   write a prompt for an aerial still of the place at that hour. I generate the images and put them in `sources/` as
   `<key>.jpg` and `fly-<key>.jpg`, 1920×1080.
3. **LTX jobs.** Write `prompts/ltx-jobs.json` in the same shape as the original: for each person a `turn-<key>` job
   (LTX-2.5 Pro, 1920×1080, 24 fps, 8 s, `camera_motion: static`) and a `fly-<key>` job. In the turn prompt keep the
   framing locked ("tripod shot, the framing never changes, does not zoom, the person stays the same size"), freeze the
   shoulders and ask for a slow, even turn of the head only. Describe each person's clothes and accessories so they stay.
4. **Render.** My LTX key is in `.env` (keys live at https://console.ltx.io; API reference at https://docs.ltx.io). Run one turn first and show me a contact sheet (ffmpeg, 2 frames per second)
   before rendering the rest. Then run all jobs with `tools/ltx.py` and `--budget`, and Alpha Gen on every turn.
5. **Pack.** Find where each turn really ends (the frame where the eyes meet the lens) and run `tools/pack.py turn`
   with `--to` set to a few frames after it; run `tools/pack.py city` for every flyover.
6. **Page.** Update `CAST`, `SLOGANS`, the palette, the big word, the footer lines and the end card. Tune each
   person's `neck` so the place never covers the face, and `dx`/`dy` so every head sits on the same axis and nothing is
   cut at the end of the push-in.
7. **Check in Chrome.** Serve with `node tools/serve.mjs .`, open it, and check every scene at the start and the end of
   its turn (`?hero=N&frame=0`, `?hero=N&frame=60`), the cut between scenes frame by frame, the finale, a phone held
   upright (390×844) and a slow network (throttled to 10 Mbit/s: the first scene should start within ~5 s).
8. **Ship.** Deploy to Vercel (`vercel deploy --prod`) and give me the link.

Rules: never print my API key; stop and ask before spending more than the budget I give you; keep the footage
weights in the README table up to date.
