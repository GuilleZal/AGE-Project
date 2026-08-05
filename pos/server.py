import os
import sys
import uvicorn
import webbrowser
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback

# Ensure the project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pos.model.database import get_connection, init_db

app = FastAPI(
    title="AGE POS API",
    description="Backend API for local web-based POS system",
    version="1.0.0"
)

# CORS middleware for local frontend development (e.g. Vite on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler — always return JSON, never plain-text 500
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"[ERROR] Unhandled exception on {request.url}:\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": str(exc)},
    )

# Database connection reference
conn = None

@app.on_event("startup")
def startup_event():
    global conn
    conn = get_connection()
    try:
        init_db(conn)
        conn.commit()
        print("Base de datos SQLite inicializada exitosamente.")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
        sys.exit(1)

    # Initialize and cache controllers in app state
    from pos.controller.login_controller import LoginController
    from pos.controller.sale_controller import SaleController
    from pos.controller.product_controller import ProductController
    from pos.controller.cash_register_controller import CashRegisterController
    from pos.controller.return_controller import ReturnController
    from pos.controller.report_controller import ReportController
    from pos.controller.user_management_controller import UserManagementController

    app.state.login_ctrl = LoginController(conn)
    app.state.sale_ctrl = SaleController(conn)
    app.state.product_ctrl = ProductController(conn)
    app.state.cash_register_ctrl = CashRegisterController(conn)
    app.state.return_ctrl = ReturnController(conn)
    app.state.report_ctrl = ReportController(conn)
    app.state.user_mgmt_ctrl = UserManagementController(conn)
    
    # Auto-open browser
    try:
        webbrowser.open("http://localhost:8000/")
    except Exception as e:
        print(f"No se pudo abrir el navegador automáticamente: {e}")

@app.on_event("shutdown")
def shutdown_event():
    global conn
    if conn:
        conn.close()
        print("Conexión de base de datos cerrada.")


# --- DTOs (Data Transfer Objects) for Requests ---

class LoginRequest(BaseModel):
    username: str
    password: str

class LogoutRequest(BaseModel):
    user_id: int

class AddBarcodeRequest(BaseModel):
    barcode: str
    quantity: float = 1.0

class AddProductIdRequest(BaseModel):
    product_id: int
    quantity: float = 1.0

class UpdateQtyRequest(BaseModel):
    product_id: int
    quantity: float

class RemoveItemRequest(BaseModel):
    product_id: int

class DiscountRequest(BaseModel):
    discount_pct: float

class SurchargeRequest(BaseModel):
    surcharge_pct: float

class CompleteSaleRequest(BaseModel):
    payment_method: str
    amount_received: int = 0


# --- API Routes ---

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "POS Server is running"}

# --- Auth Routes ---

@app.post("/api/auth/login")
def login(req: LoginRequest):
    try:
        login_ctrl = app.state.login_ctrl
        validation = login_ctrl.validate_input(req.username, req.password)
        if not validation["success"]:
            return {"success": False, "data": None, "error": validation["error"]}

        result = login_ctrl.validate(req.username, req.password)
        if not result["success"]:
            return {"success": False, "data": None, "error": result["error"]}

        user  = result["data"]["user"]
        perms = result["data"]["permissions"]

        user_dict = {
            "id":       user.id,
            "username": user.username,
            # UserRole enum → plain string
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
        perms_dict = {
            # tuple[str, ...] → list[str]  (JSON requires arrays, not tuples)
            "allowed_tabs":        list(perms.allowed_tabs),
            "cash_register_mode":  perms.cash_register_mode,
        }
        return {"success": True, "data": {"user": user_dict, "permissions": perms_dict}, "error": None}

    except Exception as exc:
        import traceback; traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": str(exc)},
        )


@app.post("/api/auth/logout")
def logout(req: LogoutRequest):
    app.state.login_ctrl.logout(req.user_id)
    return {"success": True, "error": None}


# --- Cart & Sales Routes ---

@app.get("/api/cart")
def get_cart():
    return app.state.sale_ctrl.get_cart()

@app.post("/api/cart/add-by-barcode")
def add_by_barcode(req: AddBarcodeRequest):
    result = app.state.sale_ctrl.add_by_barcode(req.barcode, req.quantity)
    # Serialize product if nested inside reactivation flow data
    if result.get("data") and result["data"].get("product"):
        prod = result["data"]["product"]
        result["data"]["product"] = {
            "id": prod.id,
            "name": prod.name,
            "barcode": prod.barcode,
            "sale_price": prod.sale_price,
            "unit_type": prod.unit_type,
        }
    return result

@app.post("/api/cart/add-by-product-id")
def add_by_product_id(req: AddProductIdRequest):
    return app.state.sale_ctrl.add_by_product_id(req.product_id, req.quantity)

@app.post("/api/cart/update-qty")
def update_qty(req: UpdateQtyRequest):
    return app.state.sale_ctrl.update_item_quantity(req.product_id, req.quantity)

@app.post("/api/cart/remove-item")
def remove_item(req: RemoveItemRequest):
    return app.state.sale_ctrl.remove_item(req.product_id)

@app.post("/api/cart/clear")
def clear_cart():
    return app.state.sale_ctrl.clear_cart()

@app.post("/api/cart/discount")
def apply_discount(req: DiscountRequest):
    return app.state.sale_ctrl.apply_discount(req.discount_pct)

@app.post("/api/cart/surcharge")
def apply_surcharge(req: SurchargeRequest):
    return app.state.sale_ctrl.apply_surcharge(req.surcharge_pct)

@app.get("/api/cart/surcharge-pct")
def get_surcharge_pct(method: str):
    return app.state.sale_ctrl.get_payment_surcharge_pct(method)

@app.post("/api/sales/complete")
def complete_sale(req: CompleteSaleRequest):
    return app.state.sale_ctrl.complete_sale(req.payment_method, req.amount_received)


# --- Products Routes ---

class CreateProductRequest(BaseModel):
    name: str
    sale_price: int
    cost_price: int
    barcode: str | None = None
    category_id: int | None = None
    stock: float = 0.0
    unit_type: str = "Unidad"
    description: str | None = None
    low_stock_threshold: int = 5

class UpdateProductRequest(BaseModel):
    name: str | None = None
    sale_price: int | None = None
    cost_price: int | None = None
    barcode: str | None = None
    category_id: int | None = None
    stock: float | None = None
    unit_type: str | None = None
    description: str | None = None
    low_stock_threshold: int | None = None

class DeleteProductsRequest(BaseModel):
    product_ids: list[int]

def _serialize_product(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "barcode": p.barcode,
        "sale_price": p.sale_price,
        "cost_price": p.cost_price,
        "stock": p.stock,
        "unit_type": getattr(p, "unit_type", "Unidad"),
        "description": p.description,
        "category_id": p.category_id,
        "low_stock_threshold": p.low_stock_threshold,
        "is_active": p.is_active,
        "created_at": p.created_at,
    }

@app.get("/api/products")
def list_products(search: str | None = None, include_inactive: bool = False, category_id: int | None = None):
    filters = {}
    if search: filters["search"] = search
    if include_inactive: filters["include_inactive"] = True
    if category_id: filters["category_id"] = category_id
    result = app.state.product_ctrl.list_products(filters or None)
    if result["success"] and result["data"]:
        result["data"] = [_serialize_product(p) for p in result["data"]]
    return result

@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    result = app.state.product_ctrl.get_product(product_id)
    if result["success"] and result["data"]:
        result["data"] = _serialize_product(result["data"])
    return result

@app.post("/api/products")
def create_product(req: CreateProductRequest):
    result = app.state.product_ctrl.create_product(req.model_dump())
    if result["success"] and result["data"]:
        result["data"] = _serialize_product(result["data"])
    return result

@app.post("/api/products/{product_id}")
def update_product(product_id: int, req: UpdateProductRequest):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    result = app.state.product_ctrl.update_product(product_id, data)
    if result["success"] and result["data"]:
        result["data"] = _serialize_product(result["data"])
    return result

@app.post("/api/products/{product_id}/delete")
def delete_product(product_id: int):
    return app.state.product_ctrl.smart_delete_products([product_id])


# --- Categories Routes ---

class CategoryRequest(BaseModel):
    name: str

@app.get("/api/categories")
def list_categories():
    result = app.state.product_ctrl.list_categories()
    if result["success"] and result["data"]:
        result["data"] = [{"id": c["id"], "name": c["name"]} for c in result["data"]]
    return result

@app.post("/api/categories")
def create_category(req: CategoryRequest):
    result = app.state.product_ctrl.create_category(req.name)
    if result["success"] and result["data"]:
        c = result["data"]
        result["data"] = {"id": c.id, "name": c.name}
    return result

@app.post("/api/categories/{category_id}")
def update_category(category_id: int, req: CategoryRequest):
    result = app.state.product_ctrl.update_category(category_id, req.name)
    if result["success"] and result["data"]:
        c = result["data"]
        result["data"] = {"id": c.id, "name": c.name}
    return result

@app.post("/api/categories/{category_id}/delete")
def delete_category(category_id: int):
    return app.state.product_ctrl.delete_category(category_id)


# --- Cash Register Routes ---

class OpenRegisterRequest(BaseModel):
    initial_amount: int

class CloseRegisterRequest(BaseModel):
    final_amount: int
    notes: str = ""

class OutflowRequest(BaseModel):
    type_: str
    amount: int
    description: str | None = None

@app.get("/api/cash/status")
def cash_status():
    return app.state.cash_register_ctrl.get_register_status()

@app.post("/api/cash/open")
def open_register(req: OpenRegisterRequest):
    return app.state.cash_register_ctrl.open_register(req.initial_amount)

@app.post("/api/cash/close")
def close_register(req: CloseRegisterRequest):
    return app.state.cash_register_ctrl.close_register(req.final_amount, req.notes)

@app.post("/api/cash/outflow")
def register_outflow(req: OutflowRequest):
    return app.state.cash_register_ctrl.register_outflow(req.type_, req.amount, req.description)

@app.get("/api/cash/history")
def cash_history():
    return app.state.cash_register_ctrl.get_history()


# --- Startup Server helper ---


def start_server():
    # Mount static files folder
    web_dir = Path(__file__).resolve().parent / "web"
    os.makedirs(web_dir, exist_ok=True)
    
    index_file = web_dir / "index.html"
    if not index_file.exists():
        with open(index_file, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>POS Sistema - Local</title>
    <style>
        body { background: #121214; color: #e1e1e6; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        h1 { color: #0078d4; }
    </style>
</head>
<body>
    <div>
        <h1>Servidor POS Local Activo</h1>
        <p>Pronto se cargará la interfaz aquí.</p>
    </div>
</body>
</html>""")

    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")

    # Run uvicorn on localhost only for security
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    start_server()
