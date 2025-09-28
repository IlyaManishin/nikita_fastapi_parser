from fastapi import FastAPI
from typing import List

import products_data

app = FastAPI()


@app.post("/products/")
def get_products_data(articles: List[int]):
    products = products_data.get_products(articles)
    return products


@app.post("/photos/")
def get_product_photos(articles: List[int]):
    photos: List[str] = products_data.get_product_photos(articles)
    return photos
