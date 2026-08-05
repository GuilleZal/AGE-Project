/**
 * views/products.js — Products management view.
 */
import { Products } from '../api.js';
import { toast } from '../app.js';

let _products   = [];
let _categories = [];
let _search     = '';

const $ = (id) => document.getElementById(id);
const fmt = (n) => '$' + Math.round(n).toLocaleString('es-AR');

function renderTable() {
  const body = $('products-tbody');
  if (!body) return;

  const filtered = _products.filter(p => {
    if (!_search) return true;
    const q = _search.toLowerCase();
    return p.name?.toLowerCase().includes(q) ||
           p.barcode?.toLowerCase().includes(q);
  });

  if (!filtered.length) {
    body.innerHTML = `
      <tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:32px">
        Sin resultados
      </td></tr>`;
    return;
  }

  const catMap = Object.fromEntries(_categories.map(c => [c.id, c.name]));

  body.innerHTML = filtered.map(p => {
    const margin = p.cost_price > 0
      ? ((p.sale_price - p.cost_price) / p.cost_price * 100).toFixed(1)
      : '—';
    const stock = p.unit_type === 'Kg'
      ? `${parseFloat(p.stock).toFixed(2)} Kg`
      : `${parseInt(p.stock)} u.`;
    const stockClass = p.stock <= p.low_stock_threshold ? 'text-danger' : 'text-success';
    const activeClass = p.is_active ? 'badge-green' : 'badge-red';
    const activeLabel = p.is_active ? 'Activo' : 'Inactivo';

    return `
      <tr>
        <td><span class="badge badge-muted" style="font-family:monospace">${p.barcode || '—'}</span></td>
        <td>${p.name}</td>
        <td>${catMap[p.category_id] ?? '—'}</td>
        <td>${fmt(p.cost_price)}</td>
        <td class="font-bold">${fmt(p.sale_price)}</td>
        <td><span class="${stockClass} font-bold">${stock}</span></td>
        <td><span class="badge ${activeClass}">${activeLabel}</span></td>
        <td>
          <div class="flex gap-2">
            <button class="btn btn-ghost btn-icon" title="Editar"
              onclick="window._productsView.openEdit(${p.id})">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
          </div>
        </td>
      </tr>`;
  }).join('');
}

async function load() {
  const [pRes, cRes] = await Promise.all([
    Products.list({ include_inactive: true }),
    Products.categories.list(),
  ]);
  if (pRes.success) {
    _products = pRes.data.map ? pRes.data : pRes.data;
    // Serialize Product dataclass if needed
    if (_products[0] && typeof _products[0] === 'object') {
      _products = _products;
    }
  }
  if (cRes.success) _categories = cRes.data ?? [];
  renderTable();
}

export function initProductsView() {
  const searchInput = $('products-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      _search = searchInput.value;
      renderTable();
    });
  }

  // Reload when tab is clicked
  document.querySelectorAll('.nav-item[data-view="productos"]').forEach(el => {
    el.addEventListener('click', load);
  });

  window._productsView = {
    openEdit(id) {
      const p = _products.find(x => x.id === id);
      if (p) toast(`Editar: ${p.name} — próximamente`, 'info');
    },
    reload: load,
  };
}
