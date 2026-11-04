/* Copyright 2026 GENESIS RT contributors, SPDX-License-Identifier: Apache-2.0 */
/* Shared verification core: pure functions, no DOM. Loaded by
 * ui/dashboard.html and ui/studio.html; tested under node from
 * tests/ui/test_dashboard_verify.py against the Python toolchain.
 * Numbers keep their file literals (a raw-preserving mini JSON parser)
 * because JSON.parse cannot distinguish 2 from 2.0, while the chain
 * hashes follow Python repr (2.0 keeps its ".0"). Consequence: a file
 * whose number literals differ textually from Python's canonical form
 * (e.g. hand-edited 2.00) reports INVALID here even if the Python
 * verifier accepts the same numeric values. Genuine passports written
 * by evidence.save_passport always use canonical literals, so they
 * verify identically on both sides. */

'use strict';


function sha256Hex(bytes) {
  const K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
             0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const len = bytes.length;
  const bitHi = Math.floor(len / 0x20000000);
  const bitLo = (len << 3) >>> 0;
  const total = (((len + 8) >> 6) + 1) << 6;
  const msg = new Uint8Array(total);
  msg.set(bytes);
  msg[len] = 0x80;
  const dv = new DataView(msg.buffer);
  dv.setUint32(total - 8, bitHi);
  dv.setUint32(total - 4, bitLo);
  const w = new Uint32Array(64);
  const rotr = (x, n) => (x >>> n) | (x << (32 - n));
  for (let off = 0; off < total; off += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(off + i * 4);
    for (let i = 16; i < 64; i++) {
      const s0 = (rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3)) >>> 0;
      const s1 = (rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10)) >>> 0;
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    let a = H[0], b = H[1], c = H[2], d = H[3];
    let e = H[4], f = H[5], g = H[6], h = H[7];
    for (let i = 0; i < 64; i++) {
      const S1 = (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) >>> 0;
      const ch = ((e & f) ^ (~e & g)) >>> 0;
      const t1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
      const S0 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) >>> 0;
      const mj = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
      const t2 = (S0 + mj) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0;
      d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0;
    H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
    H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0;
    H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
  }
  return H.map(x => x.toString(16).padStart(8, '0')).join('');
}

/* Minimal strict JSON parser preserving number literals.
 * Node shape: {t:'o',v:Map} {t:'a',v:[]} {t:'s',v:str} {t:'#',v:literal}
 *             {t:'b',v:bool} {t:'n'} */
function parseRawJson(text) {
  let pos = 0;
  const fail = (msg) => { throw new Error('JSON: ' + msg + ' at offset ' + pos); };
  const skipWs = () => {
    while (pos < text.length) {
      const c = text[pos];
      if (c !== ' ' && c !== '\t' && c !== '\n' && c !== '\r') break;
      pos++;
    }
  };
  const expect = (word) => {
    if (text.slice(pos, pos + word.length) !== word) fail('bad literal');
    pos += word.length;
  };
  const numRe = /-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?/y;
  function parseNumber() {
    numRe.lastIndex = pos;
    const m = numRe.exec(text);
    if (!m || m.index !== pos) fail('bad number');
    pos += m[0].length;
    return m[0];
  }
  function parseString() {
    pos++; // opening quote
    let out = '';
    for (;;) {
      if (pos >= text.length) fail('unterminated string');
      const c = text[pos];
      if (c === '"') { pos++; return out; }
      if (c === '\\') {
        const e = text[pos + 1];
        if (e === '"' || e === '\\' || e === '/') { out += e; pos += 2; }
        else if (e === 'b') { out += '\b'; pos += 2; }
        else if (e === 'f') { out += '\f'; pos += 2; }
        else if (e === 'n') { out += '\n'; pos += 2; }
        else if (e === 'r') { out += '\r'; pos += 2; }
        else if (e === 't') { out += '\t'; pos += 2; }
        else if (e === 'u') {
          const h = text.slice(pos + 2, pos + 6);
          if (!/^[0-9a-fA-F]{4}$/.test(h)) fail('bad \\u escape');
          let cp = parseInt(h, 16);
          pos += 6;
          if (cp >= 0xd800 && cp <= 0xdbff && text.slice(pos, pos + 2) === '\\u') {
            const h2 = text.slice(pos + 2, pos + 6);
            if (/^[0-9a-fA-F]{4}$/.test(h2)) {
              const lo = parseInt(h2, 16);
              if (lo >= 0xdc00 && lo <= 0xdfff) {
                cp = 0x10000 + ((cp - 0xd800) << 10) + (lo - 0xdc00);
                pos += 6;
              }
            }
          }
          out += String.fromCodePoint(cp);
        }
        else fail('bad escape');
      } else {
        if (c < ' ') fail('raw control character in string');
        out += c;
        pos++;
      }
    }
  }
  function parseValue(depth) {
    if (depth > 100) fail('nesting too deep');
    skipWs();
    if (pos >= text.length) fail('unexpected end');
    const c = text[pos];
    if (c === '{') {
      pos++;
      const obj = new Map();
      skipWs();
      if (text[pos] === '}') { pos++; return { t: 'o', v: obj }; }
      for (;;) {
        skipWs();
        if (text[pos] !== '"') fail('object key must be a string');
        const k = parseString();
        skipWs();
        if (text[pos] !== ':') fail('missing colon');
        pos++;
        obj.set(k, parseValue(depth + 1)); // last duplicate wins, like Python
        skipWs();
        if (text[pos] === ',') { pos++; continue; }
        if (text[pos] === '}') { pos++; return { t: 'o', v: obj }; }
        fail('expected , or }');
      }
    }
    if (c === '[') {
      pos++;
      const arr = [];
      skipWs();
      if (text[pos] === ']') { pos++; return { t: 'a', v: arr }; }
      for (;;) {
        arr.push(parseValue(depth + 1));
        skipWs();
        if (text[pos] === ',') { pos++; continue; }
        if (text[pos] === ']') { pos++; return { t: 'a', v: arr }; }
        fail('expected , or ]');
      }
    }
    if (c === '"') return { t: 's', v: parseString() };
    if (c === 't') { expect('true'); return { t: 'b', v: true }; }
    if (c === 'f') { expect('false'); return { t: 'b', v: false }; }
    if (c === 'n') { expect('null'); return { t: 'n' }; }
    if (c === '-' || (c >= '0' && c <= '9')) return { t: '#', v: parseNumber() };
    fail('unexpected character');
  }
  const root = parseValue(0);
  skipWs();
  if (pos !== text.length) fail('trailing characters');
  return root;
}

/* Canonical JSON matching Python json.dumps(sort_keys=True,
 * separators=(",", ":"), ensure_ascii=True). */
function quoteString(s) {
  let out = '"';
  for (const ch of s) {
    const cp = ch.codePointAt(0);
    if (ch === '"') out += '\\"';
    else if (ch === '\\') out += '\\\\';
    else if (ch === '\n') out += '\\n';
    else if (ch === '\r') out += '\\r';
    else if (ch === '\t') out += '\\t';
    else if (ch === '\b') out += '\\b';
    else if (ch === '\f') out += '\\f';
    else if (cp < 0x20 || cp === 0x7f) out += '\\u' + cp.toString(16).padStart(4, '0');
    else if (cp < 0x7f) out += ch;
    else if (cp <= 0xffff) out += '\\u' + cp.toString(16).padStart(4, '0');
    else {
      const t = cp - 0x10000;
      out += '\\u' + (0xd800 + (t >> 10)).toString(16) +
             '\\u' + (0xdc00 + (t & 0x3ff)).toString(16);
    }
  }
  return out + '"';
}

function cmpStr(a, b) {
  // Code-point order to match Python string sorting.
  const x = Array.from(a), y = Array.from(b);
  const n = Math.min(x.length, y.length);
  for (let i = 0; i < n; i++) {
    if (x[i] !== y[i]) return x[i].codePointAt(0) - y[i].codePointAt(0);
  }
  return x.length - y.length;
}

function canonNode(node) {
  switch (node.t) {
    case 's': return quoteString(node.v);
    case '#': return node.v;
    case 'b': return node.v ? 'true' : 'false';
    case 'n': return 'null';
    case 'a': return '[' + node.v.map(canonNode).join(',') + ']';
    case 'o': {
      const keys = Array.from(node.v.keys()).sort(cmpStr);
      return '{' + keys.map(k => quoteString(k) + ':' + canonNode(node.v.get(k))).join(',') + '}';
    }
    default: throw new Error('bad node');
  }
}

const GENESIS_PREV = 'GENESIS' + '0'.repeat(57);

function verifyChainText(text) {
  let root;
  try {
    root = parseRawJson(text);
  } catch (e) {
    return ['not valid JSON: ' + e.message];
  }
  if (root.t !== 'o') return ['passport root must be an object'];
  const get = (k) => root.v.get(k);
  const ver = get('passport_version');
  const errors = [];
  if (!ver || ver.t !== '#' || ver.v !== '1') errors.push('unsupported passport_version');
  const chain = get('chain');
  if (!chain || chain.t !== 'a' || chain.v.length === 0) {
    errors.push('empty chain');
    return errors;
  }
  const enc = new TextEncoder();
  let prev = GENESIS_PREV;
  chain.v.forEach((rec, i) => {
    if (!rec || rec.t !== 'o') { errors.push('record ' + i + ': not an object'); return; }
    for (const k of ['seq', 'kind', 'body', 'prev_hash', 'hash']) {
      if (!rec.v.get(k)) errors.push('record ' + i + ': missing ' + k);
    }
    const seq = rec.v.get('seq');
    if (!seq || seq.t !== '#' || seq.v !== String(i)) {
      errors.push('record ' + i + ': bad seq');
    }
    const ph = rec.v.get('prev_hash');
    if (!ph || ph.t !== 's' || ph.v !== prev) errors.push('record ' + i + ': prev_hash mismatch');
    const body = rec.v.get('body') || { t: 'o', v: new Map() };
    let expect = '';
    try {
      expect = sha256Hex(enc.encode(canonNode(body) + prev));
    } catch (e) {
      errors.push('record ' + i + ': cannot hash body');
    }
    const h = rec.v.get('hash');
    if (!h || h.t !== 's' || h.v !== expect) {
      const kind = rec.v.get('kind');
      errors.push('record ' + i + ' (' + (kind && kind.t === 's' ? kind.v : '?') + '): hash mismatch');
    }
    prev = (h && h.t === 's') ? h.v : '';
  });
  return errors;
}

/* HTML escaping: every interpolated passport value goes through esc(). */
function esc(v) {
  return String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

