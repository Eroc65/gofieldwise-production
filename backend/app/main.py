from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.db import Base, engine
from .models import core as model_registry
from .api import auth, leads, protected, customers, jobs, technicians, reminders, invoices, reports, estimates


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(leads.router, prefix="/api", tags=["leads"])
app.include_router(protected.router, prefix="/api", tags=["protected"])
app.include_router(customers.router, prefix="/api", tags=["customers"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(technicians.router, prefix="/api", tags=["technicians"])
app.include_router(reminders.router, prefix="/api", tags=["reminders"])
app.include_router(invoices.router, prefix="/api", tags=["invoices"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(estimates.router, prefix="/api", tags=["estimates"])

@app.get("/")
def read_root():
    return {"message": "FrontDesk Pro API is running"}
