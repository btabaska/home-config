#!/usr/bin/env python3
"""
abs-ipod-stage.py — stage Audiobookshelf content into iPod-Classic-ready form.

  NAS /volume1/audiobooks (RO CIFS at /mnt/nas-audiobooks-ro)
      -> ~/Audiobooks/<Book>.m4b     (chapter MP3s concatenated into ONE chaptered
                                       AAC .m4b: single Audiobooks entry, chapters
                                       inside, firmware-guaranteed resume position)
  NAS /volume1/podcasts   (RO CIFS at /mnt/nas-podcasts-ro)
      -> ~/Podcasts/<Show>/<episode>.mp3   (copied verbatim; iPod-native)

Also writes ~/.ipod-abs-manifest.json (metadata the push step needs). Incremental
(skips up-to-date targets), prunes staged files whose NAS source is gone, and
ABORTS before pruning if the source mounts look empty/unavailable (a NAS blip must
never wipe the local stage). Read-only on the NAS; only ever writes under the
staging dirs. The iPod is never touched here — that is abs-ipod-push.py.
"""
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
AB_SRC = Path(os.environ.get("AB_SRC", "/mnt/nas-audiobooks-ro"))
PC_SRC = Path(os.environ.get("PC_SRC", "/mnt/nas-podcasts-ro"))
AB_DST = Path(os.environ.get("AB_DST", HOME / "Audiobooks"))
PC_DST = Path(os.environ.get("PC_DST", HOME / "Podcasts"))
MANIFEST = Path(os.environ.get("MANIFEST", HOME / ".ipod-abs-manifest.json"))
LOG = Path(os.environ.get("LOG", HOME / "abs-ipod-stage.log"))
AAC_BITRATE = os.environ.get("AAC_BITRATE", "64k")
AUDIO_EXTS = {".mp3", ".m4a", ".m4b", ".aac", ".ogg", ".opus", ".flac"}

logf = open(LOG, "a", buffering=1)
def log(*a):
    msg = "{} {}".format(time.strftime("%Y-%m-%dT%H:%M:%S"), " ".join(str(x) for x in a))
    print(msg); print(msg, file=logf)

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

def ffprobe(path):
    p = run(["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(path)])
    try:
        return json.loads(p.stdout)
    except Exception:
        return {}

def tag(meta, *names):
    tags = (meta.get("format", {}) or {}).get("tags", {}) or {}
    low = {k.lower(): v for k, v in tags.items()}
    for n in names:
        if low.get(n.lower()):
            return low[n.lower()]
    return ""

def duration_ms(meta):
    try:
        return int(float(meta["format"]["duration"]) * 1000)
    except Exception:
        return 0

_num = re.compile(r"(\d+)")
def natkey(s):
    return [int(t) if t.isdigit() else t.lower() for t in _num.split(s)]

def audio_files(folder):
    return sorted([p for p in folder.iterdir()
                   if p.is_file() and p.suffix.lower() in AUDIO_EXTS and not p.name.startswith(".")],
                  key=lambda p: natkey(p.name))

def parse_epoch(datestr, fallback_path):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y"):
        try:
            return int(time.mktime(time.strptime(datestr, fmt)))
        except Exception:
            pass
    try:
        return int(fallback_path.stat().st_mtime)
    except Exception:
        return int(time.time())

# ---- safety gate: source mounts must look populated ------------------------
def mount_ok(path, min_entries=1):
    try:
        entries = [e for e in path.iterdir() if not e.name.startswith("@") and e.name != "#recycle"]
        return len(entries) >= min_entries
    except Exception:
        return False

# ---- audiobooks ------------------------------------------------------------
def stage_audiobook(book_dir):
    files = audio_files(book_dir)
    if not files:
        return None
    first = ffprobe(files[0])
    title = tag(first, "album") or book_dir.name
    author = tag(first, "artist", "album_artist", "composer") or "Unknown Author"
    out = AB_DST / (re.sub(r'[/\x00]', "_", book_dir.name) + ".m4b")

    newest_src = max(f.stat().st_mtime for f in files)
    if out.exists() and out.stat().st_mtime >= newest_src:
        meta = ffprobe(out)
        return dict(path=str(out), title=title, album=title, author=author,
                    tracklen_ms=duration_ms(meta), description="", source=str(book_dir))

    total_ms = 0
    chapters = []
    for f in files:
        m = ffprobe(f)
        d = duration_ms(m)
        chapters.append((tag(m, "title") or f.stem, total_ms, total_ms + d))
        total_ms += d

    AB_DST.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".converting.m4b")
    concat = out.with_suffix(".concat.txt")
    ffmeta = out.with_suffix(".ffmeta.txt")
    with open(concat, "w") as c:
        for f in files:
            c.write("file '%s'\n" % str(f).replace("'", "'\\''"))
    with open(ffmeta, "w") as m:
        m.write(";FFMETADATA1\n")
        for (ctitle, start, end) in chapters:
            m.write("[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n"
                    % (start, end, ctitle.replace("\n", " ")))
    cmd = ["ffmpeg", "-y", "-nostdin", "-v", "error",
           "-f", "concat", "-safe", "0", "-i", str(concat),
           "-i", str(ffmeta), "-map", "0:a", "-map_chapters", "1",
           "-c:a", "aac", "-b:a", AAC_BITRATE,
           "-metadata", "title=%s" % title, "-metadata", "album=%s" % title,
           "-metadata", "artist=%s" % author, "-metadata", "genre=Audiobook",
           "-movflags", "+faststart", str(tmp)]
    log("  encode m4b:", out.name, "(%d chapters, %.1f min)" % (len(chapters), total_ms/60000))
    r = run(cmd)
    for junk in (concat, ffmeta):
        junk.unlink(missing_ok=True)
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        log("  !! ffmpeg FAILED:", r.stderr.strip()[:300])
        return None
    os.replace(tmp, out)
    return dict(path=str(out), title=title, album=title, author=author,
                tracklen_ms=total_ms, description="", source=str(book_dir))

# ---- podcasts --------------------------------------------------------------
def stage_podcast_show(show_dir):
    entries = []
    show = show_dir.name
    for f in audio_files(show_dir):
        dst_dir = PC_DST / re.sub(r'[/\x00]', "_", show)
        dst = dst_dir / f.name
        if not (dst.exists() and dst.stat().st_size == f.stat().st_size):
            dst_dir.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_suffix(dst.suffix + ".part")
            run(["cp", "-p", str(f), str(tmp)])
            os.replace(tmp, dst)
            log("  copied episode:", show, "/", f.name)
        meta = ffprobe(dst)
        entries.append(dict(
            path=str(dst), podcast_title=show,
            episode_title=(tag(meta, "title") or dst.stem),
            description=(tag(meta, "comment", "description") or ""),
            published=parse_epoch(tag(meta, "date", "creation_time", "year"), f),
            tracklen_ms=duration_ms(meta),
            podcast_url=dst.name, podcast_rss="",
            filetype=dst.suffix.lstrip(".").lower() or "mp3",
            source=str(f)))
    return entries

# ---- prune -----------------------------------------------------------------
def prune(dst_root, valid_paths, exts):
    pruned = 0
    if not dst_root.exists():
        return 0
    for p in dst_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and str(p) not in valid_paths:
            p.unlink(missing_ok=True); pruned += 1; log("  pruned orphan:", p)
    for d in sorted([d for d in dst_root.rglob("*") if d.is_dir()], reverse=True):
        try: d.rmdir()
        except OSError: pass
    return pruned

def main():
    log("=== stage start ===")
    ab_up, pc_up = mount_ok(AB_SRC), mount_ok(PC_SRC)
    if not ab_up and not pc_up:
        log("!! both source mounts look empty/unavailable — aborting (protect the stage)")
        sys.exit(1)

    manifest = {"generated": int(time.time()), "audiobooks": [], "podcasts": []}

    if ab_up:
        log("- audiobooks:")
        for book in sorted([d for d in AB_SRC.iterdir() if d.is_dir() and not d.name.startswith("@")]):
            e = stage_audiobook(book)
            if e: manifest["audiobooks"].append(e)
    else:
        log("- audiobooks source unavailable, skipping (no prune)")

    if pc_up:
        log("- podcasts:")
        for show in sorted([d for d in PC_SRC.iterdir() if d.is_dir() and not d.name.startswith("@")]):
            manifest["podcasts"].extend(stage_podcast_show(show))
    else:
        log("- podcasts source unavailable, skipping (no prune)")

    # prune only the sides whose source was actually reachable
    if ab_up:
        prune(AB_DST, {e["path"] for e in manifest["audiobooks"]}, {".m4b"})
    if pc_up:
        prune(PC_DST, {e["path"] for e in manifest["podcasts"]}, {".mp3", ".m4a", ".aac"})

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    log("=== stage done: %d audiobooks, %d podcast episodes -> %s ==="
        % (len(manifest["audiobooks"]), len(manifest["podcasts"]), MANIFEST))

if __name__ == "__main__":
    main()
