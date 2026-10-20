"""Record the MalariaScope demo screen capture, with the learner's narration if present.

Drives the live site with Playwright: start screen, sample slide field by field
(with one mark correction), result report, accuracy page. A visible cursor is
drawn so viewers can follow clicks. If video/voice/ holds the learner's narration
(tools/make_voice.ps1), each part is timed to its voice and the audio is mixed in.

Usage:
    python tools/record_demo.py [URL]      -> video/malariascope-demo.mp4
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "video"
URL = sys.argv[1] if len(sys.argv) > 1 else "https://malariascope-two.vercel.app/"
SIZE = {"width": 1280, "height": 720}
TRIM_START = 0.8   # seconds cut from the start of the raw capture (blank page load)
SPEEDUP = 4        # repetitive fields are shown four times faster

# A visible cursor with a click ripple (headless recordings have no pointer).
CURSOR_JS = """
(() => {
  localStorage.setItem('malariascope.lang', 'en');
  const add = () => {
    if (document.getElementById('demo-cursor')) return;
    const c = document.createElement('div');
    c.id = 'demo-cursor';
    c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;' +
      'background:rgba(15,23,42,.85);border:3px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,.35);z-index:99999;' +
      'pointer-events:none;transition:transform .12s ease;';
    document.body.appendChild(c);
    document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    document.addEventListener('mousedown', e => {
      c.style.transform = 'scale(.75)';
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;left:' + e.clientX + 'px;top:' + e.clientY + 'px;width:16px;height:16px;margin:-8px 0 0 -8px;' +
        'border-radius:50%;border:3px solid #14B8A6;z-index:99998;pointer-events:none;transition:all .5s ease-out;opacity:1;';
      document.body.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(4)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
    document.addEventListener('mouseup', () => { c.style.transform = 'scale(1)'; }, true);
  };
  if (document.body) add(); else document.addEventListener('DOMContentLoaded', add);
})();
"""


def pause(s):
    time.sleep(s)


def glide_click(page, locator, settle=0.35):
    box = locator.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y, steps=28)
    pause(settle)
    page.mouse.down()
    page.mouse.up()


def glide_click_xy(page, x, y, settle=0.35):
    page.mouse.move(x, y, steps=28)
    pause(settle)
    page.mouse.down()
    page.mouse.up()


def smooth_scroll(page, y, wait=1.4):
    page.evaluate("y => window.scrollTo({top: y, behavior: 'smooth'})", y)
    pause(wait)


def wait_field(page):
    page.wait_for_function("() => MalariaScope.state.current !== null", timeout=30000)
    pause(0.4)


def mark_on_screen(page, kind, index=0):
    """Screen coordinates of a detected mark on the canvas."""
    return page.evaluate("""([kind, i]) => {
      const f = MalariaScope.state.current, c = document.getElementById('field-canvas');
      const r = c.getBoundingClientRect(), m = f[kind][i];
      return [r.left + m.x * r.width / f.width, r.top + m.y * r.height / f.height];
    }""", [kind, index])


def main():
    OUT_DIR.mkdir(exist_ok=True)
    raw_dir = OUT_DIR / "raw"
    shutil.rmtree(raw_dir, ignore_errors=True)
    # Optional narration (video/voice/*.wav from tools/make_voice.ps1): each part of
    # the capture is held at least as long as its voice-over section.
    voice_dir = OUT_DIR / "voice"
    durations = {}
    if (voice_dir / "durations.json").exists():
        durations = json.loads((voice_dir / "durations.json").read_text(encoding="utf-8-sig"))
    GAP = 1.4  # seconds of breathing room after each spoken section
    need = {k: durations.get(k, 0) + GAP for k in ("start", "demo", "result", "accuracy")}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=SIZE, record_video_dir=str(raw_dir), record_video_size=SIZE,
                                  device_scale_factor=1, locale="en-US")
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        t0 = time.monotonic()  # the recording starts with the page
        now = lambda: time.monotonic() - t0  # noqa: E731
        page.goto(URL, wait_until="networkidle")
        page.mouse.move(640, 360)
        marks = {"start": TRIM_START}

        def hold_until(section, extra_cut=0.0):
            """Wait until this section lasts `need[section]` seconds in the final video."""
            shown = now() - marks[section] - extra_cut
            if shown < need[section]:
                pause(need[section] - shown)

        # 1. Start screen: the problem and the promise.
        pause(2.5)
        page.mouse.move(980, 330, steps=40)
        pause(max(1.5, need["start"] - 10.0))
        smooth_scroll(page, 700, 3.0)
        smooth_scroll(page, 0, 1.6)
        hold_until("start")

        # 2. Sample slide, field by field.
        marks["demo"] = now()
        glide_click(page, page.locator("#sample-btn"))
        pause(1.2)
        first = True
        n = 0
        fast_start = None
        while page.locator("#result-btn").is_hidden():
            n += 1
            if n == 2:
                fast_start = now()  # repetitive fields: sped up in the edit
            glide_click(page, page.locator("#next-sample-btn"), settle=0.2)
            wait_field(page)
            if first:
                pause(2.2)
                # Remove one mark, then add a parasite the detector missed.
                x, y = mark_on_screen(page, "parasites", 0)
                glide_click_xy(page, x, y, settle=0.6)
                pause(1.2)
                glide_click(page, page.locator("#tool-par"))
                pause(0.6)
                box = page.locator("#field-canvas").bounding_box()
                glide_click_xy(page, box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.48, settle=0.6)
                pause(1.2)
                glide_click(page, page.locator("#tool-par"))  # back to the remove tool
                pause(0.8)
                first = False
            else:
                pause(1.0)
            glide_click(page, page.locator("#confirm-btn"), settle=0.25)
            pause(0.6)
        fast_end = now()
        pause(2.5)
        hold_until("demo", extra_cut=(fast_end - fast_start) * (1 - 1 / SPEEDUP))

        # 3. Result and report.
        marks["result"] = now()
        glide_click(page, page.locator("#result-btn"))
        pause(3.0)
        page.evaluate("document.getElementById('review-check').scrollIntoView({behavior: 'smooth', block: 'center'})")
        pause(2.0)
        glide_click(page, page.locator("#review-check"))
        pause(2.0)
        smooth_scroll(page, 0, 2.0)
        hold_until("result")

        # 4. Honest accuracy page, scrolled evenly over the spoken section.
        marks["accuracy"] = now()
        glide_click(page, page.locator("#nav-accuracy"))
        pause(2.5)
        stops = (420, 840, 1300, 1800)
        step = max(2.4, (need["accuracy"] - 5.0) / len(stops))
        for y in stops:
            smooth_scroll(page, y, step)
        hold_until("accuracy")

        # 5. Back to the start screen.
        page.goto(URL, wait_until="networkidle")
        pause(3.0)
        video = page.video.path()
        ctx.close()
        browser.close()

    a, b = fast_start, fast_end

    def final_time(t):
        """Raw capture time -> time in the edited video (trimmed start, sped-up fields)."""
        if t < a:
            return t - TRIM_START
        if t < b:
            return a - TRIM_START + (t - a) / SPEEDUP
        return a - TRIM_START + (b - a) / SPEEDUP + (t - b)

    out = OUT_DIR / "malariascope-demo.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    label = ("drawtext=fontfile='C\\:/Windows/Fonts/segoeuib.ttf':text='Fast-forward x4':fontsize=26:"
             "fontcolor=white:box=1:boxcolor=0x0B1B33CC:boxborderw=14:x=w-tw-36:y=h-th-36")
    graph = (
        f"[0:v]trim=start={TRIM_START}:end={a},setpts=PTS-STARTPTS[v1];"
        f"[0:v]trim=start={a}:end={b},setpts=(PTS-STARTPTS)/{SPEEDUP},{label}[v2];"
        f"[0:v]trim=start={b},setpts=PTS-STARTPTS[v3];"
        "[v1][v2][v3]concat=n=3:v=1:a=0,fps=30[v]"
    )
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(video)]
    sections = [k for k in ("start", "demo", "result", "accuracy") if (voice_dir / f"{k}.wav").exists()]
    if sections:
        for k in sections:
            cmd += ["-i", str(voice_dir / f"{k}.wav")]
        delays = []
        for i, k in enumerate(sections, 1):
            ms = int(max(0.0, final_time(marks[k]) + 0.4) * 1000)
            graph += f";[{i}:a]adelay={ms}|{ms}[a{i}]"
            delays.append(f"[a{i}]")
            print(f"  voice '{k}' starts at {ms / 1000:.1f}s")
        graph += f";{''.join(delays)}amix=inputs={len(sections)}:normalize=0[a]"
        cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    else:
        cmd += ["-filter_complex", graph, "-map", "[v]"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(f"saved {out} (fields sped up x{SPEEDUP} between {a:.1f}s and {b:.1f}s of the raw capture)")


if __name__ == "__main__":
    main()
