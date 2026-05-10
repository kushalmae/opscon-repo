/* =====================================================================
   OPSCON · Operations Console
   Vanilla JS, no framework, no CDN. Loads bundle.json + search.json
   per FSW version on demand and renders list/detail views.
   ===================================================================== */

(() => {
'use strict';

// ---------- State ----------
const state = {
  manifest: null,
  version: null,
  bundle: null,
  search: null,
  // Quick lookups built per bundle:
  idx: { command: {}, telemetry: {}, alert: {}, fdir: {}, flight_rule: {}, procedure: {} },
};

// ---------- Utilities ----------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[c]));
}

function subBadge(name) {
  if (!name) return '';
  return `<span class="sub-badge sub-${escapeHtml(name)}">${escapeHtml(name)}</span>`;
}

function sevBadge(level) {
  if (!level) return '';
  return `<span class="sev sev-${escapeHtml(level)}">${escapeHtml(level)}</span>`;
}

// ---------- Loading bundles ----------
async function loadManifest() {
  if (window.__OPSCON_DATA__) {
    state.manifest = window.__OPSCON_DATA__.manifest;
    return;
  }
  const r = await fetch('data/manifest.json');
  state.manifest = await r.json();
}

async function loadVersion(version) {
  state.version = version;
  if (window.__OPSCON_DATA__) {
    state.bundle = window.__OPSCON_DATA__.bundles[version];
    state.search = window.__OPSCON_DATA__.indexes[version];
  } else {
    const [bRes, sRes] = await Promise.all([
      fetch(`data/fsw-v${version}/bundle.json`),
      fetch(`data/fsw-v${version}/search.json`),
    ]);
    state.bundle = await bRes.json();
    state.search = await sRes.json();
  }
  buildIndexes();
  updateCounts();
  updateMeta();
}

function buildIndexes() {
  const b = state.bundle;
  state.idx = {
    command:     Object.fromEntries(b.commands.map(x =>     [x.mnemonic,    x])),
    telemetry:   Object.fromEntries(b.telemetry.map(x =>    [x.mnemonic,    x])),
    alert:       Object.fromEntries(b.alerts.map(x =>       [x.alert_id,    x])),
    fdir:        Object.fromEntries(b.fdir.map(x =>         [x.fdir_id,     x])),
    flight_rule: Object.fromEntries(b.flight_rules.map(x => [x.rule_id,     x])),
    procedure:   Object.fromEntries(b.procedures.map(x =>   [x.procedure_id,x])),
  };
}

function updateCounts() {
  const s = state.bundle.stats;
  $('#count-commands').textContent     = s.commands.toLocaleString();
  $('#count-telemetry').textContent    = s.telemetry.toLocaleString();
  $('#count-alerts').textContent       = s.alerts.toLocaleString();
  $('#count-fdir').textContent         = s.fdir.toLocaleString();
  $('#count-flight_rules').textContent = s.flight_rules.toLocaleString();
  $('#count-procedures').textContent   = s.procedures.toLocaleString();
}

function updateMeta() {
  $('#meta-build').textContent = `FSW v${state.version}`;
}

// ---------- Routing ----------
const routes = {
  '': renderHome,
  'commands': () => renderList('command'),
  'telemetry': () => renderList('telemetry'),
  'alerts': () => renderList('alert'),
  'fdir': () => renderList('fdir'),
  'flight_rules': () => renderList('flight_rule'),
  'procedures': () => renderList('procedure'),
  'command': renderCommand,
  'telemetry-item': renderTelemetry,
  'alert': renderAlert,
  'fdir-item': renderFdir,
  'flight_rule': renderFlightRule,
  'procedure': renderProcedure,
};

function parseHash() {
  const h = (location.hash || '#/').replace(/^#\/?/, '');
  const parts = h.split('/').filter(Boolean);
  return { section: parts[0] || '', id: parts.slice(1).join('/') };
}

function navigate() {
  const { section, id } = parseHash();
  highlightNav(section);
  hideSearchResults();
  let key = section;
  if (id) {
    // Map list-section → detail-route key
    if (section === 'commands')        key = 'command';
    else if (section === 'telemetry')  key = 'telemetry-item';
    else if (section === 'alerts')     key = 'alert';
    else if (section === 'fdir')       key = 'fdir-item';
    else if (section === 'flight_rules') key = 'flight_rule';
    else if (section === 'procedures') key = 'procedure';
  }
  const fn = routes[key] || renderHome;
  try {
    fn(id);
  } catch (e) {
    console.error(e);
    $('#main').innerHTML = `<div class="loading">Error: ${escapeHtml(e.message)}</div>`;
  }
}

function highlightNav(section) {
  let nav = section;
  if (!nav) nav = 'home';
  $$('.nav-item').forEach(n => {
    n.classList.toggle('active', n.dataset.section === nav);
  });
}

// ---------- Home ----------
function renderHome() {
  const b = state.bundle;
  const main = $('#main');
  clear(main);

  const hero = el('div', { class: 'hero' }, [
    el('h1', { class: 'hero-title', html:
      `<span class="hero-accent">◈</span> Operations Reference` }),
    el('p', { class: 'hero-sub' },
      `Single source of truth for spacecraft commanding, telemetry, alerts, FDIR, ` +
      `flight rules, and procedures. Fully offline — no network required.`),
  ]);
  main.appendChild(hero);

  // Stat grid
  const grid = el('div', { class: 'stat-grid' });
  const items = [
    ['commands',     b.stats.commands,     'Commands'],
    ['telemetry',    b.stats.telemetry,    'Telemetry Points'],
    ['alerts',       b.stats.alerts,       'Alerts'],
    ['fdir',         b.stats.fdir,         'FDIR Entries'],
    ['flight_rules', b.stats.flight_rules, 'Flight Rules'],
    ['procedures',   b.stats.procedures,   'Procedures'],
  ];
  for (const [route, val, label] of items) {
    const a = el('a', { class: 'stat', href: `#/${route}` }, [
      el('div', { class: 'stat-value' }, val.toLocaleString()),
      el('div', { class: 'stat-label' }, label),
    ]);
    grid.appendChild(a);
  }
  main.appendChild(grid);

  // Subsystems
  main.appendChild(el('div', { class: 'section-block' }, [
    el('h3', { class: 'section-title' }, 'Subsystems'),
    el('div', { class: 'subsystem-row', html:
      b.subsystems.map(s => subBadge(s)).join(' ') }),
  ]));
}

// ---------- Generic list renderer ----------
const LIST_DEFS = {
  command: {
    title: 'Commands',
    items: () => state.bundle.commands,
    columns: [
      { key: 'mnemonic',    label: 'Mnemonic',    cls: 'col-mnemonic',
        render: x => `<a href="#/commands/${encodeURIComponent(x.mnemonic)}">${escapeHtml(x.mnemonic)}</a>` },
      { key: 'opcode',      label: 'Opcode',      cls: 'col-mono col-narrow' },
      { key: 'subsystem',   label: 'Subsystem',   cls: 'col-narrow',
        render: x => subBadge(x.subsystem) },
      { key: 'criticality', label: 'Criticality', cls: 'col-narrow',
        render: x => sevBadge(x.criticality) },
      { key: 'description', label: 'Description' },
    ],
    href: x => `#/commands/${encodeURIComponent(x.mnemonic)}`,
    filterFields: x => `${x.mnemonic} ${x.description} ${x.opcode} ${x.subsystem}`,
  },
  telemetry: {
    title: 'Telemetry',
    items: () => state.bundle.telemetry,
    columns: [
      { key: 'mnemonic',    label: 'Mnemonic',  cls: 'col-mnemonic',
        render: x => `<a href="#/telemetry/${encodeURIComponent(x.mnemonic)}">${escapeHtml(x.mnemonic)}</a>` },
      { key: 'subsystem',   label: 'Subsystem', cls: 'col-narrow',
        render: x => subBadge(x.subsystem) },
      { key: 'type',        label: 'Type',      cls: 'col-mono col-narrow' },
      { key: 'units',       label: 'Units',     cls: 'col-mono col-narrow' },
      { key: 'apid',        label: 'APID',      cls: 'col-mono col-narrow' },
      { key: 'description', label: 'Description' },
    ],
    href: x => `#/telemetry/${encodeURIComponent(x.mnemonic)}`,
    filterFields: x => `${x.mnemonic} ${x.description} ${x.units} ${x.subsystem}`,
  },
  alert: {
    title: 'Alerts',
    items: () => state.bundle.alerts,
    columns: [
      { key: 'alert_id',    label: 'ID',          cls: 'col-id',
        render: x => `<a href="#/alerts/${encodeURIComponent(x.alert_id)}">${escapeHtml(x.alert_id)}</a>` },
      { key: 'severity',    label: 'Severity',    cls: 'col-narrow',
        render: x => sevBadge(x.severity) },
      { key: 'type',        label: 'Type',        cls: 'col-mono col-narrow' },
      { key: 'watched_telemetry', label: 'Watches', cls: 'col-mono',
        render: x => x.watched_telemetry.map(t => `<a class="mono" href="#/telemetry/${encodeURIComponent(t)}">${escapeHtml(t)}</a>`).join(', ') },
      { key: 'description', label: 'Description' },
    ],
    href: x => `#/alerts/${encodeURIComponent(x.alert_id)}`,
    filterFields: x => `${x.alert_id} ${x.description} ${x.type} ${x.severity} ${(x.watched_telemetry||[]).join(' ')}`,
  },
  fdir: {
    title: 'FDIR',
    items: () => state.bundle.fdir,
    columns: [
      { key: 'fdir_id',  label: 'ID', cls: 'col-id',
        render: x => `<a href="#/fdir/${encodeURIComponent(x.fdir_id)}">${escapeHtml(x.fdir_id)}</a>` },
      { key: 'severity', label: 'Severity', cls: 'col-narrow',
        render: x => sevBadge(x.severity) },
      { key: 'title',    label: 'Title' },
      { key: 'response', label: 'Response' },
    ],
    href: x => `#/fdir/${encodeURIComponent(x.fdir_id)}`,
    filterFields: x => `${x.fdir_id} ${x.title} ${x.response}`,
  },
  flight_rule: {
    title: 'Flight Rules',
    items: () => state.bundle.flight_rules,
    columns: [
      { key: 'rule_id',   label: 'ID', cls: 'col-id',
        render: x => `<a href="#/flight_rules/${encodeURIComponent(x.rule_id)}">${escapeHtml(x.rule_id)}</a>` },
      { key: 'subsystem', label: 'Subsystem', cls: 'col-narrow',
        render: x => subBadge(x.subsystem) },
      { key: 'rule_text', label: 'Rule' },
    ],
    href: x => `#/flight_rules/${encodeURIComponent(x.rule_id)}`,
    filterFields: x => `${x.rule_id} ${x.rule_text} ${x.operator_action} ${x.subsystem}`,
  },
  procedure: {
    title: 'Procedures',
    items: () => state.bundle.procedures,
    columns: [
      { key: 'procedure_id', label: 'ID', cls: 'col-id',
        render: x => `<a href="#/procedures/${encodeURIComponent(x.procedure_id)}">${escapeHtml(x.procedure_id)}</a>` },
      { key: 'type',         label: 'Type',         cls: 'col-mono col-narrow' },
      { key: 'criticality',  label: 'Criticality',  cls: 'col-narrow',
        render: x => sevBadge(x.criticality) },
      { key: 'duration_min', label: 'Min',          cls: 'col-narrow col-mono' },
      { key: 'title',        label: 'Title' },
    ],
    href: x => `#/procedures/${encodeURIComponent(x.procedure_id)}`,
    filterFields: x => `${x.procedure_id} ${x.title} ${x.description} ${x.type}`,
  },
};

const listState = {
  filter: '',
  sub: '',
  sev: '',
  sortKey: null,
  sortDir: 1,
};

function renderList(kind) {
  const def = LIST_DEFS[kind];
  const main = $('#main');
  clear(main);

  // Reset list state on entry
  listState.filter = '';
  listState.sub = '';
  listState.sev = '';
  listState.sortKey = null;
  listState.sortDir = 1;

  // Header
  main.appendChild(el('div', { class: 'page-header' }, [
    el('h2', { class: 'page-title' }, def.title),
    el('span', { class: 'page-subtitle' }, `FSW v${state.version}`),
  ]));

  // Filter bar
  const filterBar = el('div', { class: 'filter-bar' });
  const input = el('input', {
    class: 'filter-input', type: 'search',
    placeholder: 'Filter by mnemonic, ID, description…',
  });
  input.addEventListener('input', () => {
    listState.filter = input.value.trim().toLowerCase();
    renderTable();
  });
  filterBar.appendChild(input);

  // Subsystem chips (only if items have a 'subsystem' field)
  const sample = def.items()[0] || {};
  if ('subsystem' in sample) {
    const subs = state.bundle.subsystems;
    for (const s of subs) {
      const chip = el('button', { class: 'filter-chip', 'data-sub': s }, s);
      chip.addEventListener('click', () => {
        listState.sub = (listState.sub === s) ? '' : s;
        $$('.filter-chip[data-sub]').forEach(c =>
          c.classList.toggle('active', c.dataset.sub === listState.sub));
        renderTable();
      });
      filterBar.appendChild(chip);
    }
  }

  // Severity chips for alerts/FDIR/procedures
  if (kind === 'alert' || kind === 'fdir' || kind === 'procedure' || kind === 'command') {
    const sevs = kind === 'command'
      ? ['NOMINAL', 'HAZARDOUS', 'CRITICAL']
      : ['CRITICAL', 'WARNING', 'NOMINAL', 'HAZARDOUS'];
    for (const s of sevs) {
      const chip = el('button', { class: 'filter-chip', 'data-sev': s, html: sevBadge(s) });
      chip.addEventListener('click', () => {
        listState.sev = (listState.sev === s) ? '' : s;
        $$('.filter-chip[data-sev]').forEach(c =>
          c.classList.toggle('active', c.dataset.sev === listState.sev));
        renderTable();
      });
      filterBar.appendChild(chip);
    }
  }

  const resultCount = el('span', { class: 'filter-result-count' });
  filterBar.appendChild(resultCount);

  main.appendChild(filterBar);

  // Table
  const wrap = el('div', { class: 'table-wrap' });
  const table = el('table', { class: 'list' });
  const thead = el('thead');
  const headerRow = el('tr');
  for (const col of def.columns) {
    const th = el('th', { 'data-key': col.key }, col.label);
    th.addEventListener('click', () => {
      if (listState.sortKey === col.key) listState.sortDir = -listState.sortDir;
      else { listState.sortKey = col.key; listState.sortDir = 1; }
      renderTable();
    });
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);
  const tbody = el('tbody');
  table.appendChild(tbody);
  wrap.appendChild(table);
  main.appendChild(wrap);

  function renderTable() {
    let items = def.items();
    // Filter
    if (listState.filter) {
      const q = listState.filter;
      items = items.filter(x => def.filterFields(x).toLowerCase().includes(q));
    }
    if (listState.sub) {
      items = items.filter(x => x.subsystem === listState.sub);
    }
    if (listState.sev) {
      items = items.filter(x => (x.severity || x.criticality) === listState.sev);
    }
    // Sort
    if (listState.sortKey) {
      const k = listState.sortKey;
      const d = listState.sortDir;
      items = items.slice().sort((a, b) => {
        const av = a[k], bv = b[k];
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * d;
        return String(av || '').localeCompare(String(bv || '')) * d;
      });
    }
    // Update header sort indicators
    $$('th', thead).forEach(th => {
      th.classList.remove('sort-asc', 'sort-desc');
      if (th.dataset.key === listState.sortKey) {
        th.classList.add(listState.sortDir > 0 ? 'sort-asc' : 'sort-desc');
      }
    });

    resultCount.textContent = `${items.length.toLocaleString()} of ${def.items().length.toLocaleString()}`;

    // Cap rendering at 500 rows for performance; warn if more
    const cap = 500;
    const display = items.slice(0, cap);

    clear(tbody);
    const frag = document.createDocumentFragment();
    for (const x of display) {
      const tr = el('tr', { class: 'row-link' });
      tr.addEventListener('click', (e) => {
        // Allow inner anchor clicks to act normally
        if (e.target.tagName === 'A') return;
        location.hash = def.href(x);
      });
      for (const col of def.columns) {
        const html = col.render ? col.render(x) : escapeHtml(x[col.key] || '');
        tr.appendChild(el('td', { class: col.cls || '', html }));
      }
      frag.appendChild(tr);
    }
    tbody.appendChild(frag);

    if (items.length > cap) {
      const note = el('tr', {}, [
        el('td', { colspan: def.columns.length, class: 'section-empty',
                   style: 'text-align:center; padding:14px;' },
          `Showing first ${cap.toLocaleString()} of ${items.length.toLocaleString()} — narrow with the filter to see more.`)
      ]);
      tbody.appendChild(note);
    }
  }

  renderTable();
}

// ---------- Detail renderers ----------

function renderCommand(id) {
  const cmd = state.idx.command[id];
  if (!cmd) return notFound(id, 'command');
  const main = $('#main');
  clear(main);

  const meta = [
    ['Opcode',      `<code>${escapeHtml(cmd.opcode)}</code>`],
    ['Subsystem',   subBadge(cmd.subsystem)],
    ['Criticality', sevBadge(cmd.criticality)],
    ['FSW Min',     `<span class="mono">${escapeHtml(cmd.fsw_min_version)}</span>`],
  ];

  main.appendChild(buildDetailHeader('Command', cmd.mnemonic, cmd.description, meta));

  // Args
  if (cmd.args && cmd.args.length) {
    main.appendChild(buildSection('Arguments', buildInlineTable(
      ['Pos', 'Name', 'Type'],
      cmd.args.map(a => [a.position, a.name, a.type])
    )));
  } else {
    main.appendChild(buildSection('Arguments',
      el('div', { class: 'section-empty' }, 'No arguments')));
  }

  // Enums referenced by args
  if (cmd.enums && cmd.enums.length) {
    for (const e of cmd.enums) {
      main.appendChild(buildSection(`Enum · ${e.enum_name}`, buildInlineTable(
        ['Value', 'Label', 'Description'],
        e.values.map(v => [v.value, v.label, v.description])
      )));
    }
  }

  // Used by procedures
  main.appendChild(buildSection('Used by procedures',
    refsGrid(cmd.used_by_procedures, 'procedure')));
}

function renderTelemetry(id) {
  const t = state.idx.telemetry[id];
  if (!t) return notFound(id, 'telemetry');
  const main = $('#main');
  clear(main);

  const meta = [
    ['Type',      `<code>${escapeHtml(t.type)}</code>`],
    ['Units',     t.units ? `<code>${escapeHtml(t.units)}</code>` : '—'],
    ['APID',      `<code>${escapeHtml(t.apid)}</code>`],
    ['Subsystem', subBadge(t.subsystem)],
    ['FSW Min',   `<span class="mono">${escapeHtml(t.fsw_min_version)}</span>`],
  ];

  main.appendChild(buildDetailHeader('Telemetry', t.mnemonic, t.description, meta));

  if (t.enums && t.enums.length) {
    main.appendChild(buildSection(`Enum · ${t.enums[0].enum_name}`, buildInlineTable(
      ['Value', 'Label', 'Description'],
      t.enums.map(e => [e.value, e.label, e.description])
    )));
  }

  if (t.bitfields && t.bitfields.length) {
    main.appendChild(buildSection('Bit fields', buildInlineTable(
      ['Bit', 'Name', 'Description'],
      t.bitfields.map(b => [b.bit_position, b.bit_name, b.description])
    )));
  }

  main.appendChild(buildSection('Watched by alerts',
    refsGrid(t.watched_by_alerts, 'alert')));
  main.appendChild(buildSection('Referenced by procedures',
    refsGrid(t.referenced_by_procedures, 'procedure')));
  main.appendChild(buildSection('Referenced by flight rules',
    refsGrid(t.referenced_by_flight_rules, 'flight_rule')));
}

function renderAlert(id) {
  const a = state.idx.alert[id];
  if (!a) return notFound(id, 'alert');
  const main = $('#main');
  clear(main);

  const meta = [
    ['Severity',     sevBadge(a.severity)],
    ['Type',         `<code>${escapeHtml(a.type)}</code>`],
    ['Page',         a.page ? `<code>${escapeHtml(a.page)}</code>` : '—'],
    ['Ack required', a.ack_required ? `<code>${escapeHtml(a.ack_required)}</code>` : '—'],
    ['Auto clear',   a.auto_clear ? `<code>${escapeHtml(a.auto_clear)}</code>` : '—'],
    ['Owner',        a.owner ? `<code>${escapeHtml(a.owner)}</code>` : '—'],
  ];

  main.appendChild(buildDetailHeader('Alert', a.alert_id, a.description, meta));

  // Condition block
  main.appendChild(buildSection('Condition',
    el('div', { class: 'mono', style:
      'background:var(--bg-1);border:1px solid var(--line);padding:12px;border-radius:2px;font-size:13px;'
    }, a.condition)));

  main.appendChild(buildSection('Watched telemetry',
    refsGrid(a.watched_telemetry, 'telemetry')));

  main.appendChild(buildSection('Linked FDIR',
    refsGrid(a.fdir_id ? [a.fdir_id] : [], 'fdir')));

  if (a.notes) {
    main.appendChild(buildSection('Notes',
      el('div', { class: 'section-empty', style: 'font-style:normal; color:var(--text-2);' }, a.notes)));
  }
}

function renderFdir(id) {
  const f = state.idx.fdir[id];
  if (!f) return notFound(id, 'fdir');
  const main = $('#main');
  clear(main);

  const meta = [
    ['Severity', sevBadge(f.severity)],
  ];

  main.appendChild(buildDetailHeader('FDIR', f.fdir_id, f.title, meta));

  main.appendChild(buildSection('Response',
    el('div', { style: 'color:var(--text-1);font-size:14px;line-height:1.6;max-width:720px;' },
      f.response)));

  main.appendChild(buildSection('Associated procedure',
    refsGrid(f.associated_procedure ? [f.associated_procedure] : [], 'procedure')));

  main.appendChild(buildSection('Triggered by alerts',
    refsGrid(f.triggered_by_alerts, 'alert')));
}

function renderFlightRule(id) {
  const r = state.idx.flight_rule[id];
  if (!r) return notFound(id, 'flight rule');
  const main = $('#main');
  clear(main);

  const meta = [
    ['Subsystem', subBadge(r.subsystem)],
  ];

  main.appendChild(buildDetailHeader('Flight Rule', r.rule_id, r.rule_text, meta));

  main.appendChild(buildSection('Operator action',
    el('div', { style: 'color:var(--text-1);font-size:14px;line-height:1.6;max-width:720px;' },
      r.operator_action)));

  main.appendChild(buildSection('Related telemetry',
    refsGrid(r.related_telemetry ? [r.related_telemetry] : [], 'telemetry')));
}

function renderProcedure(id) {
  const p = state.idx.procedure[id];
  if (!p) return notFound(id, 'procedure');
  const main = $('#main');
  clear(main);

  const meta = [
    ['Type',        `<code>${escapeHtml(p.type)}</code>`],
    ['Criticality', sevBadge(p.criticality)],
    ['Duration',    `<span class="mono">${p.duration_min} min</span>`],
    ['Owner',       `<code>${escapeHtml(p.owner)}</code>`],
  ];

  main.appendChild(buildDetailHeader('Procedure', p.procedure_id, p.title, meta));

  main.appendChild(buildSection('Description',
    el('div', { style: 'color:var(--text-1);font-size:14px;line-height:1.6;max-width:720px;' },
      p.description)));

  main.appendChild(buildSection('Related commands',
    refsGrid(p.related_commands, 'command')));
  main.appendChild(buildSection('Related telemetry',
    refsGrid(p.related_telemetry, 'telemetry')));
}

// ---------- Detail builders ----------
function buildDetailHeader(kind, id, description, metaPairs) {
  const wrap = el('div', { class: 'detail' });
  wrap.appendChild(el('div', { class: 'detail-header' }, [
    el('span', { class: 'detail-kind' }, kind),
  ]));
  wrap.appendChild(el('h1', { class: 'detail-title' }, id));
  if (description) {
    wrap.appendChild(el('p', { class: 'detail-description' }, description));
  }
  const m = el('div', { class: 'detail-meta' });
  for (const [k, v] of metaPairs) {
    m.appendChild(el('div', { class: 'detail-meta-item' }, [
      el('span', { class: 'key' }, k),
      el('span', { class: 'value', html: v }),
    ]));
  }
  wrap.appendChild(m);
  return wrap;
}

function buildSection(title, content) {
  return el('div', { class: 'section-block' }, [
    el('h3', { class: 'section-title' }, title),
    content,
  ]);
}

function buildInlineTable(headers, rows) {
  const wrap = el('div', { style: 'overflow-x:auto;' });
  const t = el('table', { class: 'inline' });
  const thead = el('thead');
  const trh = el('tr');
  for (const h of headers) trh.appendChild(el('th', {}, String(h)));
  thead.appendChild(trh);
  t.appendChild(thead);
  const tbody = el('tbody');
  for (const r of rows) {
    const tr = el('tr');
    for (const cell of r) tr.appendChild(el('td', {}, String(cell ?? '')));
    tbody.appendChild(tr);
  }
  t.appendChild(tbody);
  wrap.appendChild(t);
  return wrap;
}

function refsGrid(ids, kind) {
  if (!ids || !ids.length) return el('div', { class: 'section-empty' }, 'None');
  const grid = el('div', { class: 'refs' });
  for (const id of ids) {
    const obj = state.idx[kind][id];
    if (!obj) {
      grid.appendChild(el('span', { class: 'ref-card' }, [
        el('span', { class: 'ref-id' }, id),
        el('span', { class: 'ref-text' }, '(unresolved reference)'),
      ]));
      continue;
    }
    const text = (
      obj.description ||
      obj.title ||
      obj.rule_text ||
      ''
    );
    const route = kindToRoute(kind);
    grid.appendChild(el('a', { class: 'ref-card', href: `#/${route}/${encodeURIComponent(id)}` }, [
      el('span', { class: 'ref-id' }, id),
      el('span', { class: 'ref-text' }, text),
    ]));
  }
  return grid;
}

function kindToRoute(kind) {
  return ({
    command: 'commands',
    telemetry: 'telemetry',
    alert: 'alerts',
    fdir: 'fdir',
    flight_rule: 'flight_rules',
    procedure: 'procedures',
  })[kind];
}

function notFound(id, kind) {
  const main = $('#main');
  clear(main);
  main.appendChild(el('div', { class: 'page-header' }, [
    el('h2', { class: 'page-title' }, 'Not found'),
  ]));
  main.appendChild(el('div', { class: 'section-empty', style: 'font-style:normal;' },
    `No ${kind} with ID "${id}" in this FSW version.`));
}

// ---------- Search ----------
function levenshtein1(a, b) {
  // Returns true if Levenshtein distance(a, b) <= 1
  if (a === b) return true;
  const la = a.length, lb = b.length;
  if (Math.abs(la - lb) > 1) return false;
  if (la === lb) {
    let diff = 0;
    for (let i = 0; i < la; i++) if (a[i] !== b[i]) { diff++; if (diff > 1) return false; }
    return true;
  }
  // length differs by 1 — find insertion point
  const [s, l] = la < lb ? [a, b] : [b, a];
  let i = 0, j = 0, mismatch = false;
  while (i < s.length && j < l.length) {
    if (s[i] === l[j]) { i++; j++; }
    else if (mismatch) return false;
    else { mismatch = true; j++; }
  }
  return true;
}

function tokenize(s) {
  return (s || '').toLowerCase().match(/[a-z0-9_]+/g) || [];
}

function searchQuery(q) {
  const queryTokens = tokenize(q);
  if (!queryTokens.length) return [];

  const tokenIndex = state.search.tokens;
  const allTokens = Object.keys(tokenIndex);

  // For each query token, find matching corpus tokens
  const docScores = new Map(); // docIdx -> score

  for (const qt of queryTokens) {
    const matched = new Set();
    for (const t of allTokens) {
      let weight = 0;
      if (t === qt) weight = 3;
      else if (t.startsWith(qt) && qt.length >= 2) weight = 2;
      else if (qt.length >= 4 && t.includes(qt)) weight = 1.5;
      else if (qt.length >= 4 && levenshtein1(qt, t)) weight = 1;
      if (weight > 0) {
        for (const docId of tokenIndex[t]) {
          const prev = matched.has(docId) ? 0 : weight;
          if (prev > 0) {
            matched.add(docId);
            docScores.set(docId, (docScores.get(docId) || 0) + weight);
          }
        }
      }
    }
  }

  const results = [];
  for (const [docId, score] of docScores) {
    results.push({ ...state.search.docs[docId], score });
  }
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, 80);
}

const KIND_ROUTES = {
  command: 'commands',
  telemetry: 'telemetry',
  alert: 'alerts',
  fdir: 'fdir',
  flight_rule: 'flight_rules',
  procedure: 'procedures',
};

const KIND_LABELS = {
  command: 'Commands',
  telemetry: 'Telemetry',
  alert: 'Alerts',
  fdir: 'FDIR',
  flight_rule: 'Flight Rules',
  procedure: 'Procedures',
};

const KIND_ORDER = ['command', 'telemetry', 'alert', 'fdir', 'flight_rule', 'procedure'];

function showSearchResults(results) {
  const wrap = $('#search-results');
  wrap.hidden = false;
  clear(wrap);

  const inner = el('div', { class: 'search-results-inner' });

  if (!results.length) {
    inner.appendChild(el('div', { class: 'search-empty' }, 'No results.'));
    wrap.appendChild(inner);
    return;
  }

  // Group by kind
  const byKind = {};
  for (const r of results) {
    (byKind[r.kind] = byKind[r.kind] || []).push(r);
  }

  for (const kind of KIND_ORDER) {
    const group = byKind[kind];
    if (!group || !group.length) continue;
    inner.appendChild(el('div', { class: 'search-section-header' },
      `${KIND_LABELS[kind]} · ${group.length}`));
    for (const r of group.slice(0, 25)) {
      const route = KIND_ROUTES[r.kind];
      const a = el('a', {
        class: 'search-result',
        href: `#/${route}/${encodeURIComponent(r.id)}`,
      }, [
        el('span', { class: 'search-result-id' }, r.id),
        el('span', { class: 'search-result-title' }, r.title || r.subtitle || ''),
      ]);
      a.addEventListener('click', () => {
        setTimeout(hideSearchResults, 0);
      });
      inner.appendChild(a);
    }
  }
  wrap.appendChild(inner);
}

function hideSearchResults() {
  $('#search-results').hidden = true;
  $('#search-input').value = '';
}

// ---------- Init ----------
async function init() {
  await loadManifest();

  // Populate version selector
  const sel = $('#fsw-select');
  for (const v of state.manifest.versions) {
    sel.appendChild(el('option', { value: v.version }, `v${v.version}`));
  }
  sel.value = state.manifest.default_version;
  sel.addEventListener('change', async () => {
    await loadVersion(sel.value);
    navigate();
  });

  await loadVersion(state.manifest.default_version);

  // Search
  const searchInput = $('#search-input');
  let searchTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = searchInput.value.trim();
    if (!q) { $('#search-results').hidden = true; return; }
    searchTimer = setTimeout(() => {
      const results = searchQuery(q);
      showSearchResults(results);
    }, 80);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput
        && document.activeElement.tagName !== 'INPUT') {
      e.preventDefault();
      searchInput.focus();
    } else if (e.key === 'Escape') {
      hideSearchResults();
      searchInput.blur();
    }
  });

  document.addEventListener('click', (e) => {
    const sr = $('#search-results');
    const sw = $('.search-wrap');
    if (sr.hidden) return;
    if (!sr.contains(e.target) && !sw.contains(e.target)) hideSearchResults();
  });

  window.addEventListener('hashchange', navigate);
  navigate();
}

init();
})();
