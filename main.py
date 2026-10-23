from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ==========================================
# 1. ALICI VİTRİNİ VƏ QEYDİYYATI (SESSIYA İLƏ)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def shop_page(request: Request, db: Session = Depends(get_db)):
    products = db.query(models.Product).filter(models.Product.stock_quantity > 0).all()
    customers = db.query(models.Customer).all()
    
    customer_id = request.cookies.get("customer_id")
    current_customer = None
    if customer_id:
        current_customer = db.query(models.Customer).filter(models.Customer.id == int(customer_id)).first()

    return templates.TemplateResponse(
        request=request, 
        name="shop.html", 
        context={
            "products": products, 
            "customers": customers,
            "current_customer": current_customer
        }
    )

@app.get("/customer-auth", response_class=HTMLResponse)
def customer_auth_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="customer_auth.html", 
        context={}
    )

@app.post("/customer/register")
def register_customer(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(models.Customer.email == email).first()
    if customer:
        customer.full_name = full_name
        customer.phone = phone
        customer.address = address
        customer.password = password
    else:
        customer = models.Customer(
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            password=password
        )
        db.add(customer)
    
    db.commit()
    db.refresh(customer)
    
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="customer_id", value=str(customer.id), max_age=60*60*24*30)
    return response

@app.get("/customer/logout")
def customer_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="customer_id")
    return response

# ==========================================
# 2. SATICI QEYDİYYATI VƏ İDARƏETMƏSİ
# ==========================================

@app.get("/seller/register", response_class=HTMLResponse)
def seller_register_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="seller_register.html", 
        context={}
    )

@app.post("/seller/register")
def register_seller(
    shop_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    logo_url: str = Form("https://placehold.co/100x100?text=Logo"),
    fulfillment_plan: str = Form(...),
    billing_plan: str = Form(...),
    db: Session = Depends(get_db)
):
    seller = models.Seller(
        shop_name=shop_name,
        email=email,
        phone=phone,
        password=password,
        logo_url=logo_url,
        fulfillment_plan=fulfillment_plan,
        billing_plan=billing_plan
    )
    db.add(seller)
    db.commit()
    return RedirectResponse(url=f"/seller/dashboard/{seller.id}", status_code=303)

@app.get("/seller/dashboard/{seller_id}", response_class=HTMLResponse)
def seller_dashboard(seller_id: int, request: Request, db: Session = Depends(get_db)):
    seller = db.query(models.Seller).filter(models.Seller.id == seller_id).first()
    products = db.query(models.Product).filter(models.Product.seller_id == seller_id).all()
    alerts = db.query(models.StockAlert).filter(models.StockAlert.seller_id == seller_id).order_by(models.StockAlert.id.desc()).all()
    return templates.TemplateResponse(
        request=request, 
        name="seller_dashboard.html", 
        context={"seller": seller, "products": products, "alerts": alerts}
    )

@app.post("/seller/add-product")
def seller_add_product(
    seller_id: int = Form(...),
    sku: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    stock: int = Form(...),
    db: Session = Depends(get_db)
):
    product = models.Product(
        sku=sku.upper().strip(),
        title=title,
        description=description,
        price=price,
        stock_quantity=stock,
        location="Anbara Təhvil Gözləyir",
        seller_id=seller_id
    )
    db.add(product)
    db.commit()
    return RedirectResponse(url=f"/seller/dashboard/{seller_id}", status_code=303)

# ==========================================
# 3. ANBAR İDARƏÇİSİ PANELİ (/warehouse)
# ==========================================

@app.get("/warehouse", response_class=HTMLResponse)
def warehouse_panel(request: Request, db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    orders = db.query(models.Order).order_by(models.Order.id.desc()).all()
    return templates.TemplateResponse(
        request=request, 
        name="warehouse.html", 
        context={"products": products, "orders": orders}
    )

@app.post("/warehouse/update-location")
def update_product_location(
    product_id: int = Form(...),
    location: str = Form(...),
    stock_addition: int = Form(0),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product:
        product.location = location.upper().strip()
        product.stock_quantity += stock_addition
        db.commit()
    return RedirectResponse(url="/warehouse", status_code=303)

# ==========================================
# 4. SİFARİŞ VƏ AVTOMATİK STOK NƏZARƏTİ
# ==========================================

@app.post("/order/create")
def create_order(
    customer_id: int = Form(...),
    product_id: int = Form(...),
    quantity: int = Form(1),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()

    if not product or product.stock_quantity < quantity:
        return HTMLResponse("Stokda kifayət qədər məhsul yoxdur!", status_code=400)

    product.stock_quantity -= quantity

    if product.stock_quantity <= 5:
        alert_msg = f"DİQQƏT: '{product.title}' (SKU: {product.sku}) stoku kritik həddədir! Qalan say: {product.stock_quantity} ədəd."
        alert = models.StockAlert(
            seller_id=product.seller_id,
            sku=product.sku,
            message=alert_msg
        )
        db.add(alert)

    order = models.Order(
        customer_id=customer.id,
        product_id=product.id,
        quantity=quantity,
        status="Gozleyir",
        delivery_note="Bizim Kuryer Catdirir"
    )
    db.add(order)
    db.commit()

    return RedirectResponse(url="/", status_code=303)