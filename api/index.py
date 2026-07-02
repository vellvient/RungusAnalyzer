"""
Rungus Analyzer — Web API v3.0
Flask endpoint for Vercel deployment.
All linguistic logic delegates to rungus_analyzer_lib.py (shared core library).

Endpoints:
  POST /api/analyze           { "word": "..." }
  POST /api/batch             { "words": ["...", "..."] }  (max 100)
  GET  /api/stats             — dictionary size, version, coverage info
  GET  /api/health            — health check

Author: Aifven Nelson
"""

import json
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Resolve paths ────────────────────────────────────────────────────────────
# The root API is in /api/index.py.
# The library lives in the parent project root.
# The web assets live in /rungus-analyzer-web.

_API_DIR      = Path(__file__).parent.resolve()
_PROJECT_ROOT = _API_DIR.parent.resolve()
_WEB_DIR      = _PROJECT_ROOT / "rungus-analyzer-web"

# Add the project root to sys.path so rungus_analyzer_lib can be imported
for _p in [str(_PROJECT_ROOT), str(_WEB_DIR), str(_API_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from rungus_analyzer_lib import (
        load_dictionary, analyze, generate, suggest_similar,
        PREFIXES, SUFFIXES, INFIXES, ENCLITICS,
        STANDALONE_WORDS, PROPER_NAMES, LOANWORDS,
    )
    _LIB_LOADED = True
except ImportError as e:
    _LIB_LOADED = False
    _LIB_ERROR  = str(e)

# ── Load dictionary ──────────────────────────────────────────────────────────
_DICT = None
_DICT_SIZE = 0
_DICT_ERROR = None

if _LIB_LOADED:
    _MAIN_DATASET   = _PROJECT_ROOT / "mainDataset_merged.json"
    _WEB_DICT       = _WEB_DIR / "dictionary.json"

    # Prefer full merged dataset
    for _candidate in [_MAIN_DATASET, _WEB_DICT]:
        if _candidate.exists():
            try:
                _DICT = load_dictionary(path=str(_candidate))
                _DICT_SIZE = len(_DICT)
                break
            except Exception as e:
                _DICT_ERROR = str(e)

    if _DICT is None and _WEB_DICT.exists():
        # Fall back to web-bundled dictionary.json
        try:
            with open(_WEB_DICT, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                _DICT = {k.lower(): {"headword": k, "gloss": v, "is_subentry": False}
                         for k, v in raw.items()}
                _DICT_SIZE = len(_DICT)
        except Exception as e:
            _DICT_ERROR = str(e)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _analyze_one(word: str) -> dict:
    """Run analysis and return a clean JSON-safe result dict."""
    if not _LIB_LOADED:
        return {"error": f"Library not loaded: {_LIB_ERROR}"}
    if _DICT is None:
        return {"error": f"Dictionary not loaded: {_DICT_ERROR}"}

    word = word.strip()[:100]
    if not word:
        return {"error": "empty word"}

    r = analyze(word, _DICT)

    suggestions = []
    if not r["matched"] and _DICT:
        suggestions = suggest_similar(word, _DICT, max_dist=2, max_results=5)

    return {
        "word":             r["input"],
        "matched":          r["matched"],
        "root":             r["root"],
        "root_gloss":       r["root_gloss"],
        "confidence":       round(r["confidence"], 2),
        "prefix":           r["prefix"],
        "prefix_meaning":   r["prefix_meaning"],
        "prefix2":          r.get("prefix2"),
        "prefix2_meaning":  r.get("prefix2_meaning"),
        "infix":            r["infix"],
        "infix_meaning":    r["infix_meaning"],
        "suffix":           r["suffix"],
        "suffix_meaning":   r["suffix_meaning"],
        "enclitic":         r["enclitic"],
        "enclitic_meaning": r["enclitic_meaning"],
        "breakdown":        r["breakdown"],
        "proper_name":      r["proper_name"],
        "loanword":         r["loanword"],
        "reduplication":    r["reduplication"],
        "suggestions":      suggestions,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the index.html front-end statically."""
    return send_from_directory(str(_WEB_DIR), "index.html")

@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def api_analyze():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(silent=True) or {}
    word = data.get("word", "").strip()

    if not word:
        return jsonify({"error": "No word provided"}), 400

    return jsonify(_analyze_one(word))


@app.route("/api/batch", methods=["POST", "OPTIONS"])
def api_batch():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data  = request.get_json(silent=True) or {}
    words = data.get("words", [])

    if not isinstance(words, list):
        return jsonify({"error": "words must be a list"}), 400

    words = [str(w) for w in words[:100]]
    results = [_analyze_one(w) for w in words]
    return jsonify({"results": results, "count": len(results)})


@app.route("/api/generate", methods=["POST", "OPTIONS"])
def api_generate():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if not _LIB_LOADED:
        return jsonify({"error": f"Library not loaded: {_LIB_ERROR}"}), 503

    data     = request.get_json(silent=True) or {}
    root     = data.get("root", "").strip()[:50]
    prefix   = data.get("prefix") or None
    suffix   = data.get("suffix") or None
    infix    = data.get("infix") or None
    enclitic = data.get("enclitic") or None

    if not root:
        return jsonify({"error": "root is required"}), 400

    surface = generate(root, prefix=prefix, suffix=suffix,
                       infix=infix, enclitic=enclitic)
    return jsonify({"root": root, "surface_form": surface,
                    "prefix": prefix, "suffix": suffix,
                    "infix": infix, "enclitic": enclitic})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify({
        "version":       "3.0",
        "dict_size":     _DICT_SIZE,
        "prefixes":      len(PREFIXES) if _LIB_LOADED else 0,
        "suffixes":      len(SUFFIXES) if _LIB_LOADED else 0,
        "infixes":       len(INFIXES)  if _LIB_LOADED else 0,
        "enclitics":     len(ENCLITICS) if _LIB_LOADED else 0,
        "standalone_words": len(STANDALONE_WORDS) if _LIB_LOADED else 0,
        "proper_names":  len(PROPER_NAMES) if _LIB_LOADED else 0,
        "loanwords":     len(LOANWORDS)   if _LIB_LOADED else 0,
        "corpus_coverage_pct": 93.0,
        "lib_loaded":    _LIB_LOADED,
        "dict_loaded":   _DICT is not None,
    })


@app.route("/api/health", methods=["GET"])
def api_health():
    ok = _LIB_LOADED and _DICT is not None
    return jsonify({
        "status":  "ok" if ok else "degraded",
        "lib":     _LIB_LOADED,
        "dict":    _DICT is not None,
    }), 200 if ok else 503


if __name__ == "__main__":
    app.run(debug=True, port=5000)
