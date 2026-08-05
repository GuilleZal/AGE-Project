/**
 * api.js — Centralized fetch wrapper for the FastAPI backend.
 * All endpoints return { success, data, error }.
 */
const API_BASE = 'http://localhost:8000';

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(`${API_BASE}${path}`, opts);
    return await res.json();
  } catch (err) {
    return { success: false, data: null, error: `Error de conexión: ${err.message}` };
  }
}

const get  = (path)        => request('GET',  path);
const post = (path, body)  => request('POST', path, body);
const del  = (path, body)  => request('DELETE', path, body);

// ── Auth ────────────────────────────────────────────────────────────────────
export const Auth = {
  login:  (username, password) => post('/api/auth/login',  { username, password }),
  logout: (user_id)            => post('/api/auth/logout', { user_id }),
};

// ── Cart & Sales ─────────────────────────────────────────────────────────────
export const Cart = {
  get:          ()                          => get('/api/cart'),
  addBarcode:   (barcode, quantity = 1)     => post('/api/cart/add-by-barcode',    { barcode, quantity }),
  addProductId: (product_id, quantity = 1)  => post('/api/cart/add-by-product-id', { product_id, quantity }),
  updateQty:    (product_id, quantity)      => post('/api/cart/update-qty',         { product_id, quantity }),
  removeItem:   (product_id)               => post('/api/cart/remove-item',        { product_id }),
  clear:        ()                          => post('/api/cart/clear'),
  discount:     (discount_pct)             => post('/api/cart/discount',           { discount_pct }),
  surcharge:    (surcharge_pct)            => post('/api/cart/surcharge',          { surcharge_pct }),
  getSurchargePct: (method)               => get(`/api/cart/surcharge-pct?method=${encodeURIComponent(method)}`),
  completeSale: (payment_method, amount_received = 0) =>
    post('/api/sales/complete', { payment_method, amount_received }),
};

// ── Products ─────────────────────────────────────────────────────────────────
export const Products = {
  list:       (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return get(`/api/products${qs ? '?' + qs : ''}`);
  },
  get:        (id)          => get(`/api/products/${id}`),
  create:     (data)        => post('/api/products',       data),
  update:     (id, data)    => post(`/api/products/${id}`, data),
  delete:     (id)          => post(`/api/products/${id}/delete`),
  categories: {
    list:   ()            => get('/api/categories'),
    create: (name)        => post('/api/categories',       { name }),
    update: (id, name)    => post(`/api/categories/${id}`, { name }),
    delete: (id)          => post(`/api/categories/${id}/delete`),
  },
};

// ── Cash Register ─────────────────────────────────────────────────────────────
export const Cash = {
  status:        ()                           => get('/api/cash/status'),
  open:          (initial_amount)             => post('/api/cash/open',  { initial_amount }),
  close:         (final_amount, notes = '')   => post('/api/cash/close', { final_amount, notes }),
  outflow:       (type_, amount, description) => post('/api/cash/outflow', { type_, amount, description }),
  history:       ()                           => get('/api/cash/history'),
};

// ── Reports ───────────────────────────────────────────────────────────────────
export const Reports = {
  summary: (start_date, end_date) => {
    const qs = new URLSearchParams({ start_date, end_date }).toString();
    return get(`/api/reports/summary?${qs}`);
  },
};
