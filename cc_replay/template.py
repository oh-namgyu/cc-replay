"""Static page assets for the generated replay.

Everything the page needs lives in this module: markup, CSS and JS are inlined
into a single file so a replay opens from disk with no network access at all.
"""

CSS = """
:root {
  color-scheme: dark;
  --bg: #12141a; --panel: #191c24; --panel-2: #1f232d; --line: #2b303c;
  --bar: #161922; --fg: #e6e8ee; --fg-dim: #99a0b0; --accent: #7aa2f7;
  --user: #9ece6a; --error: #f7768e; --warn: #e0af68; --think: #bb9af7;
  --sub: #7dcfff; --ok: #73daca; --flash: rgba(122, 162, 247, .22);
}
@media (prefers-color-scheme: light) {
  :root {
    color-scheme: light;
    --bg: #f6f7f9; --panel: #ffffff; --panel-2: #eef0f5; --line: #d3d8e2;
    --bar: #ffffff; --fg: #1b1f28; --fg-dim: #555f70; --accent: #2b56c4;
    --user: #276b2c; --error: #b3132c; --warn: #7a4c00; --think: #5c33ad;
    --sub: #0f5f78; --ok: #0f6b5c; --flash: rgba(43, 86, 196, .14);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg); padding-bottom: 68px;
  font: 14px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
pre, code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

.topbar {
  position: sticky; top: 0; z-index: 10; background: var(--panel);
  border-bottom: 1px solid var(--line); padding: 10px 18px;
}
.topbar h1 { margin: 0 0 4px; font-size: 16px; font-weight: 600; }
.crumbs { color: var(--fg-dim); font-size: 12px; display: flex; flex-wrap: wrap; gap: 10px; }
.stats { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.stat {
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 6px;
  padding: 3px 9px; font-size: 12px; color: var(--fg-dim);
}
.stat b { color: var(--fg); font-weight: 600; }
.note { color: var(--warn); }
.tokenline { margin-top: 6px; font-size: 11.5px; color: var(--fg-dim); }
.tokenline b { color: var(--fg); font-weight: 600; }

.timeline { max-width: 1000px; margin: 0 auto; padding: 18px 18px 30px; }
.step {
  display: flex; gap: 12px; padding: 8px 0; border-radius: 8px;
  content-visibility: auto; contain-intrinsic-size: auto 120px;
  transition: opacity .18s ease, background-color .45s ease;
}
.step.future { opacity: .25; }
.step.flash { background: var(--flash); }
.when {
  flex: 0 0 62px; text-align: right; color: var(--fg-dim);
  font-size: 11px; padding-top: 3px; font-variant-numeric: tabular-nums;
}
.what { flex: 1 1 auto; min-width: 0; }
.who {
  font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
  color: var(--fg-dim); margin-bottom: 3px;
}
.step-user .who { color: var(--user); }
.step-assistant .who { color: var(--accent); }
.step-thinking .who { color: var(--think); }
.step-subagent .who { color: var(--sub); }
.is-meta { opacity: .55; }

.text, .code {
  margin: 0; padding: 9px 11px; background: var(--panel); border: 1px solid var(--line);
  border-radius: 7px; white-space: pre-wrap; overflow-wrap: anywhere; overflow-x: auto;
}
.code { background: var(--panel-2); font-size: 12.5px; max-height: 460px; overflow-y: auto; }
.code-error { border-color: var(--error); }
.step-user .text { border-left: 3px solid var(--user); }
.step-assistant .text { border-left: 3px solid var(--accent); }

.md { white-space: normal; }
.md p, .md li { white-space: pre-wrap; }
.md p { margin: 0 0 8px; }
.md > :last-child { margin-bottom: 0; }
.md-h { margin: 10px 0 6px; font-size: 14px; font-weight: 600; line-height: 1.3; }
.md-h1 { font-size: 16px; }
.md-list { margin: 4px 0 8px; padding-left: 22px; }
.md-code {
  white-space: pre; margin: 8px 0; background: var(--panel-2);
  border: 1px solid var(--line); border-radius: 7px; padding: 9px 11px;
  font-size: 12.5px; overflow-x: auto;
}
.md code, .md-inline {
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 4px;
  padding: 0 4px; font-size: 12.5px;
}
.md-code code { background: none; border: 0; padding: 0; font-size: inherit; }
.md a { color: var(--accent); }

details { border: 1px solid var(--line); border-radius: 7px; background: var(--panel); }
summary {
  cursor: pointer; padding: 7px 11px; display: flex; align-items: baseline;
  gap: 9px; list-style: none;
}
summary::-webkit-details-marker { display: none; }
summary::before { content: "\\25B8"; color: var(--fg-dim); font-size: 11px; }
details[open] > summary::before { content: "\\25BE"; }
details[open] > summary { border-bottom: 1px solid var(--line); }
.tool-name { color: var(--accent); font-weight: 600; flex: 0 0 auto; }
.tool-brief {
  color: var(--fg-dim); font-size: 12.5px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; flex: 1 1 auto; min-width: 0;
}
.tool-row.is-error { border-color: var(--error); }
.tool-row.is-error .tool-name { color: var(--error); }
.tool-detail { padding: 9px 11px; display: grid; gap: 5px; }
.label { font-size: 11px; text-transform: uppercase; color: var(--fg-dim); letter-spacing: .06em; }
.badge {
  flex: 0 0 auto; font-size: 10.5px; padding: 1px 7px; border-radius: 99px;
  border: 1px solid currentColor;
}
.badge-error { color: var(--error); }
.badge-pending { color: var(--warn); }
.badge-ok { color: var(--ok); }
.badge-loud {
  color: var(--bg); background: var(--warn); border-color: var(--warn);
  font-weight: 700; padding: 2px 9px;
}
.think-row, .think-row > summary { color: var(--think); }
.think-row .text { border-left: 3px solid var(--think); }
.unknown-row > summary { color: var(--fg-dim); }
.sys-row { display: flex; gap: 8px; align-items: flex-start; }
.sys-tag { color: var(--warn); font-size: 11px; padding-top: 10px; flex: 0 0 auto; }
.sys-row .text { flex: 1 1 auto; min-width: 0; font-size: 12.5px; color: var(--fg-dim); }

.subagent { margin: 8px 0 0 4px; padding-left: 14px; border-left: 2px solid var(--sub); }
.subagent .step { padding: 6px 0; }
.sub-head { color: var(--sub); font-size: 12px; }
.empty, .noscript { color: var(--fg-dim); padding: 20px 0; }

.foot {
  max-width: 1000px; margin: 0 auto; padding: 0 18px 24px;
  display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
  color: var(--fg-dim); font-size: 11.5px; border-top: 1px solid var(--line);
  padding-top: 14px;
}
.playbar {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 20; background: var(--bar);
  border-top: 1px solid var(--line); padding: 9px 16px;
  display: flex; align-items: center; gap: 10px;
}
.pb-btn {
  background: var(--panel-2); color: var(--fg); border: 1px solid var(--line);
  border-radius: 6px; padding: 5px 11px; cursor: pointer; font-size: 13px; line-height: 1;
}
.pb-btn:hover { border-color: var(--accent); color: var(--accent); }
.pb-btn:disabled { opacity: .4; cursor: default; }
.pb-range { flex: 1 1 auto; min-width: 80px; accent-color: var(--accent); cursor: pointer; }
.pb-count {
  flex: 0 0 auto; color: var(--fg-dim); font-size: 12px;
  font-variant-numeric: tabular-nums; min-width: 86px; text-align: right;
}
.pb-hint { flex: 0 0 auto; color: var(--fg-dim); font-size: 11px; }
@media (max-width: 640px) {
  .step { gap: 8px; }
  .when { flex-basis: 46px; }
  .pb-hint { display: none; }
}
"""

JS = """
(function () {
  var holder = document.getElementById('session-data');
  var data = {};
  try { data = JSON.parse(holder.textContent || '{}'); } catch (err) { data = {}; }
  var LABELS = {
    user: 'User', assistant: 'Claude', thinking: 'Thinking', tool_call: 'Tool',
    system: 'System', unknown: 'Raw event', subagent: 'Subagent'
  };
  var PATH_TOOLS = { Read: 1, Write: 1, Edit: 1, NotebookEdit: 1 };

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function clock(stamp) {
    // Read straight off the ISO string rather than converting to local time:
    // the header span is UTC too, and a shared replay must read identically
    // for every viewer regardless of their timezone.
    return stamp ? esc(String(stamp).slice(11, 19)) : '';
  }

  function brief(value, limit) {
    var flat = String(value || '').replace(/\\s+/g, ' ').trim();
    return flat.length > limit ? flat.slice(0, limit) + '\\u2026' : flat;
  }

  // --- micro markdown -----------------------------------------------------
  // Input is escaped FIRST, so every transform below runs on inert text and
  // no markup from the transcript can ever reach the DOM.
  function inlineMd(text) {
    return text
      .replace(/`([^`\\n]+)`/g, '<code class="md-inline">$1</code>')
      // Links only for http(s). The lookbehind keeps image syntax ![alt](url)
      // out: images must never load, so they stay literal text.
      .replace(/(?<!!)\\[([^\\]\\n]+)\\]\\((https?:\\/\\/[^\\s)]+)\\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/\\*\\*([^*\\n]+)\\*\\*/g, '<strong>$1</strong>')
      .replace(/(^|[\\s(])\\*([^*\\n]+)\\*/g, '$1<em>$2</em>')
      .replace(/(^|[\\s(])_([^_\\n]+)_/g, '$1<em>$2</em>');
  }

  function mdBlocks(chunk) {
    var lines = chunk.split('\\n');
    var out = '', para = [], list = null, index, line, head, bullet, ordered;
    function flushPara() {
      if (para.length) { out += '<p>' + inlineMd(para.join('\\n')) + '</p>'; para = []; }
    }
    function flushList() { if (list) { out += '</' + list + '>'; list = null; } }
    for (index = 0; index < lines.length; index++) {
      line = lines[index];
      head = /^(#{1,3})\\s+(.*)$/.exec(line);
      bullet = /^\\s*[-*+]\\s+(.*)$/.exec(line);
      ordered = /^\\s*\\d+[.)]\\s+(.*)$/.exec(line);
      if (head) {
        flushPara(); flushList();
        out += '<div class="md-h md-h' + head[1].length + '">' + inlineMd(head[2]) + '</div>';
      } else if (bullet || ordered) {
        flushPara();
        var tag = bullet ? 'ul' : 'ol';
        if (list !== tag) { flushList(); out += '<' + tag + ' class="md-list">'; list = tag; }
        out += '<li>' + inlineMd((bullet || ordered)[1]) + '</li>';
      } else if (!line.trim()) {
        flushPara(); flushList();
      } else {
        flushList(); para.push(line);
      }
    }
    flushPara(); flushList();
    return out;
  }

  function markdown(raw) {
    var text = esc(raw);
    var fence = /```([A-Za-z0-9_+#.-]*)\\n?([\\s\\S]*?)```/g;
    var out = '', cursor = 0, match;
    while ((match = fence.exec(text)) !== null) {
      out += mdBlocks(text.slice(cursor, match.index));
      out += '<pre class="md-code"><code>' + match[2] + '</code></pre>';
      cursor = fence.lastIndex;
    }
    return out + mdBlocks(text.slice(cursor));
  }

  // --- step rendering -----------------------------------------------------
  function toolBrief(step) {
    var parsed = null;
    try { parsed = JSON.parse(step.tool_input); } catch (err) { parsed = null; }
    if (parsed && typeof parsed === 'object' && !(parsed instanceof Array)) {
      if (step.tool_name === 'Bash' && parsed.command) { return brief(parsed.command, 80); }
      if (PATH_TOOLS[step.tool_name] && (parsed.file_path || parsed.path)) {
        return brief(parsed.file_path || parsed.path, 120);
      }
      var keys = Object.keys(parsed);
      if (keys.length) { return brief(keys[0] + ': ' + parsed[keys[0]], 120); }
    }
    return brief(step.tool_input, 140);
  }

  function toolRow(step) {
    var badge = '';
    if (step.is_error) { badge = '<span class="badge badge-error">error</span>'; }
    else if (step.pending) { badge = '<span class="badge badge-pending">no result</span>'; }
    var out = '<details class="tool-row' + (step.is_error ? ' is-error' : '') + '"><summary>';
    out += '<span class="tool-name">' + esc(step.tool_name) + '</span>';
    out += '<span class="tool-brief">' + esc(toolBrief(step)) + '</span>';
    out += badge + '</summary><div class="tool-detail">';
    out += '<div class="label">Input</div><pre class="code">' + esc(step.tool_input) + '</pre>';
    if (!step.pending) {
      out += '<div class="label">Result</div>';
      out += '<pre class="code' + (step.is_error ? ' code-error' : '') + '">';
      out += esc(step.result) + '</pre>';
    }
    return out + '</div></details>';
  }

  function body(step) {
    if (step.kind === 'tool_call') { return toolRow(step); }
    if (step.kind === 'user' || step.kind === 'assistant') {
      return '<div class="text md">' + markdown(step.text) + '</div>';
    }
    if (step.kind === 'thinking') {
      return '<details class="think-row"><summary>' + esc(brief(step.text, 90)) +
        '</summary><pre class="text">' + esc(step.text) + '</pre></details>';
    }
    if (step.kind === 'unknown') {
      return '<details class="unknown-row"><summary>' + esc(step.subtype || 'unknown') +
        '</summary><pre class="code">' + esc(step.raw) + '</pre></details>';
    }
    if (step.kind === 'system') {
      return '<div class="sys-row"><span class="sys-tag">' + esc(step.subtype || 'system') +
        '</span><pre class="text">' + esc(step.text) + '</pre></div>';
    }
    if (step.kind === 'subagent') { return '<div class="sub-head">subagent activity</div>'; }
    return '<pre class="text">' + esc(step.text) + '</pre>';
  }

  function build(steps) {
    var out = '', index, step;
    for (index = 0; index < steps.length; index++) {
      step = steps[index];
      out += '<section class="step step-' + esc(step.kind) + (step.is_meta ? ' is-meta' : '') + '">';
      out += '<div class="when">' + clock(step.timestamp) + '</div><div class="what">';
      out += '<div class="who">' + esc(LABELS[step.kind] || step.kind) + '</div>';
      out += body(step);
      if (step.children && step.children.length) {
        out += '<div class="subagent">' + build(step.children) + '</div>';
      }
      out += '</div></section>';
    }
    return out;
  }

  var steps = data.steps || [];
  var target = document.getElementById('timeline');
  target.innerHTML = steps.length
    ? build(steps)
    : '<p class="empty">No renderable steps in this transcript.</p>';

  // --- playback -----------------------------------------------------------
  var nodes = target.querySelectorAll(':scope > .step');
  var total = nodes.length;
  var range = document.getElementById('pb-range');
  var counter = document.getElementById('pb-count');
  var playButton = document.getElementById('pb-play');
  var prevButton = document.getElementById('pb-prev');
  var nextButton = document.getElementById('pb-next');
  var cursor = total - 1;
  var painted = -1;
  var active = false;
  var timer = null;
  var flashTimer = null;

  function paint() {
    if (!active) { return; }
    var from = painted < 0 ? 0 : Math.min(painted, cursor);
    var to = painted < 0 ? total - 1 : Math.max(painted, cursor);
    for (var index = from; index <= to && index < total; index++) {
      nodes[index].classList.toggle('future', index > cursor);
    }
    painted = cursor;
  }

  function label() {
    counter.textContent = total ? (cursor + 1) + ' / ' + total : '0 / 0';
    range.value = String(cursor < 0 ? 0 : cursor);
  }

  function reveal() {
    var node = nodes[cursor];
    if (!node) { return; }
    node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    node.classList.add('flash');
    if (flashTimer) { clearTimeout(flashTimer); }
    flashTimer = setTimeout(function () { node.classList.remove('flash'); }, 600);
  }

  function seek(next, scroll) {
    if (!total) { return; }
    active = true;
    cursor = Math.max(0, Math.min(total - 1, next));
    paint();
    label();
    if (scroll) { reveal(); }
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    playButton.textContent = '\\u25B6';
  }

  function play() {
    if (!total) { return; }
    if (cursor >= total - 1) { seek(0, true); }
    playButton.textContent = '\\u275A\\u275A';
    timer = setInterval(function () {
      if (cursor >= total - 1) { stop(); return; }
      seek(cursor + 1, true);
    }, 600);
  }

  function toggle() { if (timer) { stop(); } else { play(); } }

  prevButton.addEventListener('click', function () { stop(); seek(cursor - 1, true); });
  nextButton.addEventListener('click', function () { stop(); seek(cursor + 1, true); });
  playButton.addEventListener('click', toggle);
  range.addEventListener('input', function () { stop(); seek(parseInt(range.value, 10), true); });

  document.addEventListener('keydown', function (event) {
    // The range input handles arrows and space itself once focused.
    if (event.target === range) { return; }
    if (event.key === 'ArrowLeft') { stop(); seek(cursor - 1, true); event.preventDefault(); }
    else if (event.key === 'ArrowRight') { stop(); seek(cursor + 1, true); event.preventDefault(); }
    else if (event.key === ' ') { toggle(); event.preventDefault(); }
  });

  range.max = String(total ? total - 1 : 0);
  label();
  if (!total) {
    prevButton.disabled = nextButton.disabled = playButton.disabled = range.disabled = true;
  }
})();
"""

TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="cc-replay %%VERSION%%">
<title>cc-replay &middot; %%TITLE%%</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2312141a'/%3E%3Cpath d='M12 9l12 7-12 7z' fill='%237aa2f7'/%3E%3C/svg%3E">
<style>%%CSS%%</style>
</head>
<body>
<header class="topbar">
  <h1>%%TITLE%%</h1>
  <div class="crumbs">
    <span>%%PROJECT%%</span><span>%%DATE%%</span><span>%%BRANCH%%</span>
    <span class="mono">%%SESSION_ID%%</span><span>cli %%CC_VERSION%%</span>
  </div>
  <div class="stats">
    <span class="stat"><b>%%TURNS%%</b> turns</span>
    <span class="stat"><b>%%TOOLS%%</b> tool calls</span>
    <span class="stat"><b>%%DURATION%%</b> long</span>
    %%NOTES%%
  </div>
  <div class="tokenline">
    tokens <b>%%TOKENS_IN%%</b> in / <b>%%TOKENS_OUT%%</b> out
    &middot; cache <b>%%TOKENS_CACHE_READ%%</b> read / <b>%%TOKENS_CACHE_WRITE%%</b> written
  </div>
</header>
<main class="timeline" id="timeline">
  <p class="noscript">Enable JavaScript to view this replay timeline.</p>
</main>
<footer class="foot">
  <span>Generated by cc-replay %%VERSION%%</span>
  <span>%%GENERATED%%</span>
  %%REDACTION_BADGE%%
</footer>
<div class="playbar" id="playbar">
  <button class="pb-btn" id="pb-prev" type="button" aria-label="Previous step">&#9664;</button>
  <button class="pb-btn" id="pb-play" type="button" aria-label="Play or pause">&#9654;</button>
  <button class="pb-btn" id="pb-next" type="button" aria-label="Next step">&#9654;&#124;</button>
  <input class="pb-range" id="pb-range" type="range" min="0" max="0" value="0"
         aria-label="Timeline position">
  <span class="pb-count" id="pb-count">0 / 0</span>
  <span class="pb-hint">&#8592;/&#8594; step &middot; space play</span>
</div>
<script type="application/json" id="session-data">%%SESSION_JSON%%</script>
<script>%%JS%%</script>
</body>
</html>
"""
