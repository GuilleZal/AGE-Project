/**
 * views/sales.js — Sales terminal view logic.
 * Handles: barcode search, cart management, F5/F6 shortcuts,
 * Kg product weight dialog, payment methods, and sale confirmation.
 */
import { Cart } from '../api.js';
import { toast } from '../app.js';

let _cart       = [];
let _selectedId = null;
let _surchargeLabel = 'Recargo';
let _discountLabel  = 'Descuento';

// ── Formatting helpers ────────────────────────────────────────────────────────
const fmt = (n) => '$' + Math.round(n).toLocaleString('es-AR');
const fmtQty = (qty, unit) =>
  unit === 'Kg' ? `${parseFloat(qty).toFixed(3)} Kg` : `${parseInt(qty)} u.`;

// ── DOM refs ─────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── Cart rendering ────────────────────────────────────────────────────────────
function renderCart(items, total) {
  _cart = items ?? [];
  const body   = $('cart-body');
  const empty  = $('cart-empty');
  const totEl  = $('total-amount');

  if (!body) return;

  if (!_cart.length) {
    body.innerHTML = '';
    empty?.classList.remove('hidden');
    if (totEl) totEl.textContent = fmt(0);
    return;
  }

  empty?.classList.add('hidden');

  body.innerHTML = _cart.map(item => {
    const sel = item.product_id === _selectedId ? 'selected' : '';
    const qty = fmtQty(item.quantity, item.unit_type);
    return `
      <tr class="${sel}" data-pid="${item.product_id}" id="cart-row-${item.product_id}">
        <td class="truncate" style="max-width:180px" title="${item.name}">${item.name}</td>
        <td>${qty}</td>
        <td>${fmt(item.unit_price)}</td>
        <td class="font-bold">${fmt(item.subtotal)}</td>
        <td>
          <button class="btn btn-danger btn-icon" onclick="window._salesView.removeItem(${item.product_id})"
            title="Eliminar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
            </svg>
          </button>
        </td>
      </tr>`;
  }).join('');

  if (totEl) totEl.textContent = fmt(total ?? _cart.reduce((a, i) => a + i.subtotal, 0));

  // Re-bind row click for selection
  body.querySelectorAll('tr[data-pid]').forEach(row => {
    row.addEventListener('click', () => {
      _selectedId = parseInt(row.dataset.pid);
      body.querySelectorAll('tr').forEach(r => r.classList.remove('selected'));
      row.classList.add('selected');
    });
  });
}

// ── Refresh cart from API ─────────────────────────────────────────────────────
async function refreshCart() {
  const prevId = _selectedId;
  const res = await Cart.get();
  if (res.success) {
    renderCart(res.data.items, res.data.total);
    // Restore selection
    if (prevId) {
      _selectedId = prevId;
      const row = document.getElementById(`cart-row-${prevId}`);
      if (row) row.classList.add('selected');
    }
  }
}

// ── Barcode / product search ──────────────────────────────────────────────────
async function onBarcodeSearch(e) {
  if (e.key !== 'Enter') return;
  const input   = $('barcode-search');
  const barcode = input.value.trim();
  if (!barcode) return;

  const res = await Cart.addBarcode(barcode);
  input.value = '';
  input.focus();

  if (!res.success) {
    toast(res.error || 'Producto no encontrado', 'error');
    return;
  }

  _selectedId = res.data?.product_id ?? null;
  toast(`${res.data?.name ?? 'Producto'} agregado`, 'success', 1800);
  await refreshCart();
}

// ── F5 / F6 shortcuts ────────────────────────────────────────────────────────
async function adjustQty(delta) {
  if (!_selectedId) return;
  const item = _cart.find(i => i.product_id === _selectedId);
  if (!item) return;
  if (item.unit_type === 'Kg') return; // No F5/F6 for Kg products

  const newQty = Math.max(1, item.quantity + delta);
  const res = await Cart.updateQty(_selectedId, newQty);
  if (res.success) await refreshCart();
  else toast(res.error, 'error');
}

// ── Remove item ───────────────────────────────────────────────────────────────
async function removeItem(productId) {
  const res = await Cart.removeItem(productId);
  if (res.success) {
    if (_selectedId === productId) _selectedId = null;
    await refreshCart();
  } else {
    toast(res.error, 'error');
  }
}

// ── Clear cart ────────────────────────────────────────────────────────────────
async function clearCart() {
  if (!_cart.length) return;
  if (!confirm('¿Vaciar el carrito?')) return;
  await Cart.clear();
  _selectedId = null;
  await refreshCart();
}

// ── Payment method ────────────────────────────────────────────────────────────
let _selectedPayment = 'cash';

function selectPayment(method) {
  _selectedPayment = method;
  document.querySelectorAll('.payment-method-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.method === method);
  });
}

// ── Kg weight modal ───────────────────────────────────────────────────────────
let _pendingKgProductId = null;
let _kgPricePerUnit     = 0;

function openKgModal(productId, productName, pricePerKg) {
  _pendingKgProductId = productId;
  _kgPricePerUnit     = pricePerKg;
  $('kg-modal-title').textContent = productName;
  $('kg-price-label').textContent = `${fmt(pricePerKg)} / Kg`;
  $('kg-weight-input').value = '';
  $('kg-amount-input').value = '';
  $('kg-modal-overlay').classList.add('open');
  setTimeout(() => $('kg-weight-input').focus(), 100);
}

function closeKgModal() {
  $('kg-modal-overlay').classList.remove('open');
  _pendingKgProductId = null;
}

async function confirmKgModal() {
  const weight = parseFloat($('kg-weight-input').value);
  if (!weight || weight <= 0) {
    toast('Ingrese un peso mayor a 0', 'error');
    return;
  }
  closeKgModal();
  const res = await Cart.addProductId(_pendingKgProductId, weight);
  if (res.success) {
    _selectedId = _pendingKgProductId;
    await refreshCart();
    toast(`Agregado ${weight.toFixed(3)} Kg`, 'success', 1800);
  } else {
    toast(res.error, 'error');
  }
}

// ── Complete sale ─────────────────────────────────────────────────────────────
async function completeSale() {
  if (!_cart.length) { toast('El carrito está vacío', 'error'); return; }

  let received = 0;
  if (_selectedPayment === 'cash') {
    const inp = $('received-amount');
    received = parseInt(inp?.value?.replace(/\D/g, '') ?? '0') || 0;
  }

  const res = await Cart.completeSale(_selectedPayment, received);
  if (res.success) {
    toast('¡Venta confirmada!', 'success', 3000);
    _selectedId = null;
    selectPayment('cash');
    const inp = $('received-amount');
    if (inp) inp.value = '';
    $('change-amount').textContent = fmt(0);
    await refreshCart();
  } else {
    toast(res.error || 'Error al confirmar la venta', 'error');
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
export function initSalesView() {
  const searchInput = $('barcode-search');
  if (searchInput) searchInput.addEventListener('keydown', onBarcodeSearch);

  // Payment method buttons
  document.querySelectorAll('.payment-method-btn').forEach(btn => {
    btn.addEventListener('click', () => selectPayment(btn.dataset.method));
  });

  // Confirm sale button
  $('confirm-sale-btn')?.addEventListener('click', completeSale);

  // Clear cart button
  $('clear-cart-btn')?.addEventListener('click', clearCart);

  // Kg modal events
  $('kg-confirm-btn')?.addEventListener('click', confirmKgModal);
  $('kg-cancel-btn')?.addEventListener('click', closeKgModal);

  // Kg weight → amount sync
  $('kg-weight-input')?.addEventListener('input', () => {
    const w = parseFloat($('kg-weight-input').value) || 0;
    $('kg-amount-input').value = w > 0 ? fmt(w * _kgPricePerUnit) : '';
  });

  // Kg amount → weight sync
  $('kg-amount-input')?.addEventListener('input', () => {
    const raw = $('kg-amount-input').value.replace(/[^\d]/g, '');
    const amount = parseFloat(raw) || 0;
    $('kg-weight-input').value = amount > 0 ? (amount / _kgPricePerUnit).toFixed(3) : '';
  });

  // Received amount → change display
  $('received-amount')?.addEventListener('input', () => {
    const received = parseInt($('received-amount').value.replace(/\D/g, '') || '0');
    const total    = _cart.reduce((a, i) => a + i.subtotal, 0);
    const change   = Math.max(0, received - total);
    $('change-amount').textContent = fmt(change);
  });

  // Load initial cart
  refreshCart();

  // Expose API to app.js for F5/F6
  window._salesView = {
    handleF5: () => adjustQty(-1),
    handleF6: () => adjustQty(+1),
    removeItem,
    openKgModal,
  };
}
