from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
from contextlib import asynccontextmanager
from threading import Thread
import logging

import products_data
from prices_parser import periodic_price_update
from orders.orders_parser import period_sales_scheduler


class ProductsRequest(BaseModel):
    articles: List[int] = []
    tokens: List[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = Thread(target=periodic_price_update, daemon=True)
    thread.start()
    thread = Thread(target=period_sales_scheduler, daemon=True)
    thread.start()
    logging.info("Periodic price update thread started")
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/products/")
def get_products_data(body: ProductsRequest) -> list[products_data.Product]:
    products = products_data.get_products(body.articles, body.tokens)
    return products


@app.post("/photos/")
def get_product_photos(articles: List[int]):
    photos: List[str] = products_data.get_product_photos(articles)
    return photos
