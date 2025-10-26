from fastapi import FastAPI
from typing import List, Optional

import products_data

app = FastAPI()


@app.post("/products/")
def get_products_data(articles: List[int], token: Optional[str] = None) -> list[products_data.Product]:
    products = products_data.get_products(articles, token)
    return products


@app.post("/photos/")
def get_product_photos(articles: List[int]):
    photos: List[str] = products_data.get_product_photos(articles)
    return photos
