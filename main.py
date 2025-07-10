from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import logging

import products_data
from products_data import Product

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("logger.log"),
    ]
)


@app.post("/products/")
def get_products_data(articles: List[int]):
    products = products_data.get_products(articles)
    return products


@app.post("/photos/")
def get_product_photos(articles: List[int]):
    photos: List[str] = products_data.get_product_photos(articles)
    return photos
