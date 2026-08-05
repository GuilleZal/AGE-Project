/**
 * views/cash.js — Cash register view logic.
 */
import { Cash } from '../api.js';
import { toast } from '../app.js';

const $ = (id) => document.getElementById(id);
const fmt = (n) => '$' + Math.round(n ?? 0).toLocaleString('es-AR');

async function loadStatus() {
  const res = await Cash.status();
  if (!res.success) { toast(res.error, 'error'); return; }

  const { active, register, balance } = res.data;
  const dot   = $('cash-status-dot');
  const label = $('cash-status-label');
  const openBtn  = $('cash-open-btn');
  const closeBtn = $('cash-close-btn');

  if (dot)   dot.className   = `status-dot ${active ? 'active' : 'inactive'}`;
  if (label) label.textContent = active ? 'Caja Abierta' : 'Caja Cerrada';
  if (openBtn)  openBtn.classList.toggle('hidden', active);
  if (closeBtn) closeBtn.classList.toggle('hidden', !active);

  if (active && balance) {
    const el = (id, val) => { const e = $(id); if (e) e.textContent = val; };
    el('cash-opening',  fmt(balance.opening));
    el('cash-sales',    fmt(balance.sales));
    el('cash-outflows', fmt(balance.outflows));
    el('cash-expected', fmt(balance.expected));
    if (register) el('cash-opener', register.username ?? '—');
  }
}

async function openRegister() {
  const amountStr = prompt('Ingrese el monto de apertura (en pesos):');
  if (amountStr === null) return;
  const amount = parseInt(amountStr.replace(/\D/g, '') ?? '0');
  if (isNaN(amount) || amount < 0) { toast('Monto inválido', 'error'); return; }

  const res = await Cash.open(amount);
  if (res.success) { toast('Caja abierta correctamente', 'success'); loadStatus(); }
  else toast(res.error, 'error');
}

async function closeRegister() {
  const amountStr = prompt('Ingrese el monto contado en caja al cierre:');
  if (amountStr === null) return;
  const amount = parseInt(amountStr.replace(/\D/g, '') ?? '0');
  if (isNaN(amount) || amount < 0) { toast('Monto inválido', 'error'); return; }

  const notes = prompt('Motivo de cierre (opcional):') ?? '';
  const res = await Cash.close(amount, notes);
  if (res.success) {
    const diff = res.data?.diff ?? 0;
    const sign = diff >= 0 ? '+' : '';
    toast(`Caja cerrada. Diferencia: ${sign}${fmt(diff)}`, diff === 0 ? 'success' : 'info', 5000);
    loadStatus();
  } else toast(res.error, 'error');
}

export function initCashView() {
  $('cash-open-btn')?.addEventListener('click', openRegister);
  $('cash-close-btn')?.addEventListener('click', closeRegister);

  document.querySelectorAll('.nav-item[data-view="caja"]').forEach(el => {
    el.addEventListener('click', loadStatus);
  });

  window._cashView = { reload: loadStatus };
}
