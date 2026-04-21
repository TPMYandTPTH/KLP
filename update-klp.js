#!/usr/bin/env node
/**
 * update-klp.js
 *
 * Phase 1: Apply Korean text replacements from KLP_Content_Korean.xlsx to HTML files.
 *   - Column C = current text, D = alt1, E = alt2 (preferred)
 *   - E > D > skip
 *
 * Phase 2: Remove deprecated pages ta-team.html and casual-interview.html,
 *   and strip all <a> links pointing to them (removing parent <li> if applicable).
 *
 * Flags:
 *   --dry-run (default)   show summary, write nothing
 *   --apply               actually modify files and delete deprecated pages
 */

const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');
const cheerio = require('cheerio');

const APPLY = process.argv.includes('--apply');
const DRY_RUN = !APPLY;

const ROOT = __dirname;
const XLSX_PATH = path.join(ROOT, 'KLP_Content_Korean.xlsx');

// Sheet → HTML file mapping.
// Sheets that don't exactly match {name}.html need an explicit alias.
const SHEET_TO_FILE = {
  'index':             'index.html',
  'about-tp':          'about-tp.html',
  'salary-benefits':   'salary-and-benefits.html',
  'hiring-process':    'hiring-process.html',
  'open-jobs':         'open-jobs.html',
  'relocation-visa':   'relocation-visa.html',
  'why-my-th':         'why-malaysia-thailand.html',
  'testimonials':      'testimonials.html',
  'office-env':        'office-environment.html',
  'daily-life':        'daily-life-malaysia.html',
  'cost-living':       'cost-of-living.html',
  'area-office':       'area-around-office.html',
};

const DEPRECATED_PAGES = ['ta-team.html', 'casual-interview.html'];

// --------- helpers ---------

function log(...args) { console.log(...args); }
function warn(...args) { console.log('  [warn]', ...args); }

function resolveSheetToFile(sheetName) {
  if (sheetName === 'Reference') return null;
  if (sheetName.endsWith('(REMOVE)')) return null;
  return SHEET_TO_FILE[sheetName] || `${sheetName}.html`;
}

// Match href to a deprecated page (with optional query / fragment / leading ./)
function hrefMatchesDeprecated(href, deprecatedFile) {
  if (!href) return false;
  const stripped = href.replace(/^\.?\//, '').split('#')[0].split('?')[0];
  return stripped === deprecatedFile;
}

// ------ Phase 1: content replacement ------

function phase1(wb) {
  log('==========================================');
  log('PHASE 1 — Content replacement');
  log('==========================================');
  log(DRY_RUN ? '(dry-run — no files will be written)' : '(apply mode)');
  log('');

  const overallSummary = [];

  for (const sheetName of wb.SheetNames) {
    const targetFile = resolveSheetToFile(sheetName);
    if (targetFile === null) {
      log(`[skip sheet] ${sheetName}`);
      continue;
    }

    const filePath = path.join(ROOT, targetFile);
    log(`--- Sheet: "${sheetName}" → ${targetFile} ---`);

    if (!fs.existsSync(filePath)) {
      warn(`target file does not exist, skipping`);
      overallSummary.push({ sheet: sheetName, file: targetFile, status: 'file-missing' });
      continue;
    }

    let html = fs.readFileSync(filePath, 'utf8');
    const originalLen = html.length;

    const sheet = wb.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });

    let total = 0, applied = 0, skipped = 0, notFound = 0, conflicts = 0;
    const appliedMap = new Map(); // C → replacement, to detect conflicts

    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      const current = row[2]; // C
      const altD = row[3] || ''; // D
      const altE = row[4] || ''; // E

      if (!current || current === '') continue;
      total++;

      const replacement = altE || altD || null;
      if (!replacement) {
        skipped++;
        continue;
      }

      // Conflict detection: same C appears earlier with different replacement
      if (appliedMap.has(current)) {
        const prev = appliedMap.get(current);
        if (prev !== replacement) {
          warn(`conflict at row ${i + 1}: "${current.slice(0, 40)}..." already mapped to a different replacement, skipping this one`);
          conflicts++;
          continue;
        }
        // Same C and same replacement → already applied, count as applied (no-op)
        applied++;
        continue;
      }

      if (!html.includes(current)) {
        notFound++;
        warn(`not found in HTML (row ${i + 1}): "${current.slice(0, 60)}${current.length > 60 ? '...' : ''}"`);
        continue;
      }

      html = html.split(current).join(replacement); // plain str.replace-all, no regex
      appliedMap.set(current, replacement);
      applied++;
    }

    if (!DRY_RUN && html.length !== originalLen) {
      fs.writeFileSync(filePath, html, 'utf8');
    }

    log(`  total rows: ${total} | applied: ${applied} | skipped (no D/E): ${skipped} | not found: ${notFound} | conflicts: ${conflicts}`);
    overallSummary.push({ sheet: sheetName, file: targetFile, total, applied, skipped, notFound, conflicts });
  }

  log('');
  log('Phase 1 summary:');
  log('  Sheet'.padEnd(22) + 'File'.padEnd(32) + 'Total  Applied  Skipped  NotFound  Conflicts');
  for (const s of overallSummary) {
    if (s.status === 'file-missing') {
      log(`  ${s.sheet.padEnd(20)} ${s.file.padEnd(30)} [FILE MISSING]`);
    } else {
      log(`  ${s.sheet.padEnd(20)} ${s.file.padEnd(30)} ${String(s.total).padStart(5)}  ${String(s.applied).padStart(7)}  ${String(s.skipped).padStart(7)}  ${String(s.notFound).padStart(8)}  ${String(s.conflicts).padStart(9)}`);
    }
  }
  log('');
}

// ------ Phase 2: deprecated page removal ------

function phase2() {
  log('==========================================');
  log('PHASE 2 — Remove deprecated pages');
  log('==========================================');
  log(DRY_RUN ? '(dry-run — no files will be deleted/modified)' : '(apply mode)');
  log('');

  // Step 1: delete deprecated files
  log('--- Deleting deprecated HTML files ---');
  for (const page of DEPRECATED_PAGES) {
    const p = path.join(ROOT, page);
    if (fs.existsSync(p)) {
      if (DRY_RUN) {
        log(`  [would delete] ${page}`);
      } else {
        fs.unlinkSync(p);
        log(`  [deleted]      ${page}`);
      }
    } else {
      log(`  [already removed] ${page}`);
    }
  }
  log('');

  // Step 2: strip links from all other HTML files
  log('--- Stripping links from remaining HTML files ---');
  const allHtml = fs.readdirSync(ROOT).filter(f => f.endsWith('.html') && !DEPRECATED_PAGES.includes(f));

  const stripSummary = [];

  for (const file of allHtml) {
    const filePath = path.join(ROOT, file);
    const html = fs.readFileSync(filePath, 'utf8');

    // Use cheerio with xmlMode off + decodeEntities false to minimize formatting changes
    const $ = cheerio.load(html, { decodeEntities: false, xmlMode: false });

    let stripped = 0;
    const removedDetails = [];

    for (const deprecated of DEPRECATED_PAGES) {
      $('a').each((_, el) => {
        const href = $(el).attr('href');
        if (!hrefMatchesDeprecated(href, deprecated)) return;

        const parent = el.parent;
        const parentTag = parent && parent.name ? parent.name : null;

        if (parentTag === 'li') {
          removedDetails.push(`<li><a href="${href}">…</a></li>`);
          $(el.parent).remove();
        } else {
          removedDetails.push(`<a href="${href}">…</a> (parent: ${parentTag || 'n/a'})`);
          $(el).remove();
        }
        stripped++;
      });
    }

    if (stripped > 0) {
      const newHtml = $.html();
      if (!DRY_RUN) {
        fs.writeFileSync(filePath, newHtml, 'utf8');
      }
    }

    stripSummary.push({ file, stripped, removedDetails });
  }

  log('  File'.padEnd(38) + 'Links stripped');
  for (const s of stripSummary) {
    log(`  ${s.file.padEnd(35)}  ${s.stripped}`);
    if (s.stripped > 0 && process.argv.includes('--verbose')) {
      for (const d of s.removedDetails) {
        log(`    - ${d}`);
      }
    }
  }
  log('');
}

// ------ main ------

(function main() {
  log('update-klp.js starting...');
  log('  mode:', DRY_RUN ? 'DRY-RUN' : 'APPLY');
  log('  xlsx:', XLSX_PATH);
  log('  html root:', ROOT);
  log('');

  if (!fs.existsSync(XLSX_PATH)) {
    console.error('ERROR: xlsx file not found at', XLSX_PATH);
    process.exit(1);
  }

  const wb = XLSX.readFile(XLSX_PATH);

  phase1(wb);
  phase2();

  log('==========================================');
  log(DRY_RUN ? 'Dry-run complete. Re-run with --apply to commit changes.' : 'Apply complete.');
  log('==========================================');
})();
