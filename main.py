import os
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents
from schemas import Devotional, Progress, Reward, Product, Order, User

app = FastAPI(title="Sanctuary Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== Helpers =====================

def collection_name(model_cls) -> str:
    return model_cls.__name__.lower()


def ensure_db():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")


# ===================== Root & Health =====================

@app.get("/")
def read_root():
    return {"message": "Sanctuary Builder Backend is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# ===================== Schemas Endpoint (for Admin tooling) =====================

@app.get("/schema")
def get_schema_overview():
    return {
        "collections": [
            collection_name(User),
            collection_name(Devotional),
            collection_name(Progress),
            collection_name(Reward),
            collection_name(Product),
            collection_name(Order),
        ]
    }


# ===================== Devotionals =====================

class DevotionalCreate(BaseModel):
    date: date
    title_en: str
    title_zh: str
    passage_en: Optional[str] = None
    passage_zh: Optional[str] = None
    content_en: str
    content_zh: str
    reflection_prompt_en: Optional[str] = None
    reflection_prompt_zh: Optional[str] = None


@app.get("/api/devotionals/today")
def get_today_devotional(locale: str = Query("en", pattern="^(en|zh)$")):
    ensure_db()
    today = date.today()
    docs = get_documents(collection_name(Devotional), {"date": today.isoformat()}, limit=1)
    if not docs:
        return {
            "date": today.isoformat(),
            "title": "No devotional yet" if locale == "en" else "今天还没有灵修内容",
            "passage": None,
            "content": "Come back later." if locale == "en" else "稍后再来。",
            "reflection_prompt": None,
        }
    d = docs[0]
    return {
        "date": d.get("date") if isinstance(d.get("date"), str) else d.get("date").isoformat() if d.get("date") else today.isoformat(),
        "title": d.get("title_en") if locale == "en" else d.get("title_zh"),
        "passage": d.get("passage_en") if locale == "en" else d.get("passage_zh"),
        "content": d.get("content_en") if locale == "en" else d.get("content_zh"),
        "reflection_prompt": d.get("reflection_prompt_en") if locale == "en" else d.get("reflection_prompt_zh"),
    }


@app.get("/api/devotionals")
def get_devotional_by_date(qdate: str = Query(..., description="YYYY-MM-DD"), locale: str = Query("en", pattern="^(en|zh)$")):
    ensure_db()
    docs = get_documents(collection_name(Devotional), {"date": qdate}, limit=1)
    if not docs:
        raise HTTPException(status_code=404, detail="Devotional not found")
    d = docs[0]
    return {
        "date": qdate,
        "title": d.get("title_en") if locale == "en" else d.get("title_zh"),
        "passage": d.get("passage_en") if locale == "en" else d.get("passage_zh"),
        "content": d.get("content_en") if locale == "en" else d.get("content_zh"),
        "reflection_prompt": d.get("reflection_prompt_en") if locale == "en" else d.get("reflection_prompt_zh"),
    }


@app.post("/api/devotionals")
def create_devotional(payload: DevotionalCreate):
    ensure_db()
    data = payload.model_dump()
    # Store date as ISO string for consistent querying
    data["date"] = payload.date.isoformat()
    inserted_id = create_document(collection_name(Devotional), data)
    return {"id": inserted_id}


# ===================== Progress & Rewards =====================

class CompleteRequest(BaseModel):
    user_id: str
    date: Optional[date] = None


@app.post("/api/progress/complete")
def complete_today(payload: CompleteRequest):
    ensure_db()
    target_date = (payload.date or date.today()).isoformat()
    doc = {
        "user_id": payload.user_id,
        "date": target_date,
        "completed": True,
        "points_earned": 10,
    }
    inserted_id = create_document(collection_name(Progress), doc)
    return {"id": inserted_id, "points_earned": 10}


@app.get("/api/progress/stats")
def progress_stats(user_id: str = Query(...)):
    ensure_db()
    items = get_documents(collection_name(Progress), {"user_id": user_id})
    # Sort by date string ascending
    def parse_d(d):
        try:
            if isinstance(d, str):
                return datetime.strptime(d, "%Y-%m-%d").date()
            if isinstance(d, date):
                return d
            return None
        except Exception:
            return None

    items = [i for i in items if parse_d(i.get("date")) is not None]
    items.sort(key=lambda x: parse_d(x.get("date")))

    # Calculate current streak (consecutive days up to today)
    today = date.today()
    streak = 0
    day_ptr = today
    completed_dates = {parse_d(i.get("date")) for i in items if i.get("completed")}
    while day_ptr in completed_dates:
        streak += 1
        day_ptr = day_ptr - timedelta(days=1)

    total_points = sum(int(i.get("points_earned", 0)) for i in items)

    return {
        "days_completed": len(completed_dates),
        "current_streak": streak,
        "total_points": total_points,
    }


# ===================== Marketplace =====================

class ProductCreate(BaseModel):
    sku: str
    title_en: str
    title_zh: str
    description_en: Optional[str] = None
    description_zh: Optional[str] = None
    price: float
    currency: str = "USD"
    categories: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list)
    attributes: Dict[str, str] = Field(default_factory=dict)
    status: str = "active"


@app.get("/api/products")
def list_products(locale: str = Query("en", pattern="^(en|zh)$")):
    ensure_db()
    docs = get_documents(collection_name(Product))
    out = []
    for d in docs:
        out.append({
            "sku": d.get("sku"),
            "title": d.get("title_en") if locale == "en" else d.get("title_zh"),
            "description": d.get("description_en") if locale == "en" else d.get("description_zh"),
            "price": d.get("price"),
            "currency": d.get("currency", "USD"),
            "media_urls": d.get("media_urls", []),
            "status": d.get("status", "active"),
        })
    return out


@app.post("/api/products")
def create_product(payload: ProductCreate):
    ensure_db()
    inserted_id = create_document(collection_name(Product), payload.model_dump())
    return {"id": inserted_id}


# ===================== Orders =====================

class OrderCreate(BaseModel):
    user_id: str
    items: List[Dict[str, Any]]
    currency: str = "USD"


@app.post("/api/orders")
def create_order(payload: OrderCreate):
    ensure_db()
    total = 0.0
    for item in payload.items:
        qty = float(item.get("qty", 1))
        price = float(item.get("price", 0))
        total += qty * price
    record = {
        "user_id": payload.user_id,
        "items": payload.items,
        "total_amount": round(total, 2),
        "currency": payload.currency,
        "status": "pending",
    }
    inserted_id = create_document(collection_name(Order), record)
    return {"id": inserted_id, "total_amount": record["total_amount"]}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
