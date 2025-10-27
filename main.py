from fastapi import FastAPI
from typing import List
from pydantic import BaseModel

import products_data


class ProductsRequest(BaseModel):
    articles: List[int] = []
    tokens: List[str]


app = FastAPI()


@app.post("/products/")
def get_products_data(body: ProductsRequest) -> list[products_data.Product]:
    products = products_data.get_products(body.articles, body.tokens)
    return products


@app.post("/photos/")
def get_product_photos(articles: List[int]):
    photos: List[str] = products_data.get_product_photos(articles)
    return photos
