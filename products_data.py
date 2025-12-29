from typing import List
from pydantic import BaseModel
from concurrent import futures
import requests
import time
import json
import logging

from prices_parser import get_prices_data, ArticlePrice

MAX_THREADS = 10


class Product(BaseModel):
    article: int
    photo_url: str
    category: str
    seller_name: str
    url: str
    price: int  # spp price
    stocks: int
    spp_percent: float


class Size(BaseModel):
    price: float
    discountedPrice: float


def get_basket(article: int) -> str:
    vol = article // 100000
    part = article // 1000

    limits = [
        143, 287, 431, 719, 1007, 1061, 1115, 1169, 1313, 1601,
        1655, 1919, 2045, 2189, 2405, 2621, 2837, 3053, 3269, 3485,
        3701, 3917, 4133, 4349, 4565, 4877, 5189, 5501, 5813, 6125,
        6437, 6749, 7061, 7373, 7685, 7997, 8309
    ]

    basket_num = next((i + 1 for i, v in enumerate(limits) if vol <= v), 38)

    return f"https://basket-{basket_num:02d}.wbbasket.ru/vol{vol}/part{part}/{article}"



def safe_requests_get(url: str) -> dict:
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            return "-"

        data = json.loads(resp.text)
        return data
    except:
        return None


def get_seller_name(basket: str) -> str:
    url = f"{basket}/info/sellers.json"
    data = safe_requests_get(url)
    if not data:
        return "-"
    return data.get("supplierName", "-")


def get_category(basket: str) -> str:
    url = f"{basket}/info/ru/card.json"
    data = safe_requests_get(url)
    if not data:
        return "-"
    return data.get("subj_name", "-")


def get_photo_url(basket: str) -> str:
    url = f"{basket}/images/big/1.webp"
    photo_url = f'=ARRAYFORMULA(IMAGE("{url}"))'
    return photo_url


def get_products_stocks(product_data: dict) -> int:
    quantity = 0
    try:
        sizes = product_data.get("sizes", [])
        for i in sizes:
            stocks = i.get("stocks", [])
            for j in stocks:
                quantity += j.get("qty", 0)
    except:
        pass
    return quantity


def get_spp_price(product_data: dict) -> int:
    sizes = product_data.get("sizes", [])
    if len(sizes) > 0:
        size = sizes[0]
        spp_price = size.get("price", {}).get("product", 0) // 100
    return spp_price


def get_spp_percent(nm_id: int, product_data: dict, prices_data: List[ArticlePrice]) -> float:
    price_retail, sale_without_spp = 0, 0
    for i in prices_data:
        if i.nm_id == nm_id:
            sale_without_spp = i.discount
            price_retail = i.price_retail
    try:
        price = int(round(price_retail * (100 - sale_without_spp) / 100))
    except:
        price = 0

    spp_price = get_spp_price(product_data)
    try:
        if spp_price == price:
            spp_percent = 0
        if spp_price == 0:
            spp_percent = 0
        else:
            spp_percent = round((100 * (1 - (spp_price / price))), 2)
    except:
        spp_percent = 0
    return spp_percent


def _get_product_data(article: int, prices_data: List[ArticlePrice]) -> Product:
    tryings = 5
    data = None
    is_valid = False
    product = None
    for i in range(tryings):
        status = None
        try:
            url = f"https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-380708&spp=30&lang=ru&nm={article}"
            resp = requests.get(url)
            status = resp.status_code
            if status != 200:
                raise Exception()
            text = resp.text
            data = json.loads(text)
            product_data: dict = data['products'][0]
            is_valid = True
            break
        except:
            if status == 200:
                break
            time.sleep(10)

    basket = get_basket(article)
    photo_url = get_photo_url(basket)
    if not is_valid:
        product = Product(article=article,
                          photo_url=photo_url,
                          category="-",
                          seller_name="-",
                          url=f"https://www.wildberries.ru/catalog/{article}/detail.aspx",
                          price=0,
                          stocks=0,
                          spp_percent=0)
        return product

    product = Product(article=article,
                      photo_url=photo_url,
                      category=get_category(basket),
                      seller_name=get_seller_name(basket),
                      url=f"https://www.wildberries.ru/catalog/{article}/detail.aspx",
                      price=get_spp_price(product_data),
                      stocks=get_products_stocks(product_data),
                      spp_percent=get_spp_percent(article, product_data, prices_data))

    return product


def _get_product_task(article: int, *args):
    try:
        res = _get_product_data(article, *args)
        return res
    except Exception as err:
        logging.error(f"Article error: {article}")
        logging.exception(err)
    return


def get_products(articles: List[int], tokens: list[str]) -> List[Product]:
    all_data = []
    prices_data = get_prices_data()
    with futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        all_futures = []
        for article in articles:
            all_futures.append(executor.submit(
                _get_product_task, article, prices_data))
        for future in futures.as_completed(all_futures):
            try:
                res: Product = future.result()
                if not res:
                    continue
                all_data.append(res)

            except Exception as err:
                logging.exception(err)
    return all_data


def get_product_photos(articles: List[int]) -> List[str]:
    result = [get_photo_url(get_basket(article)) for article in articles]
    return result

print(get_basket(707022674))