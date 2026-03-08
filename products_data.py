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


def get_basket(article, isFull=True):
    vol = article // 100000
    part = article // 1000

    basket_ranges = [
        (143, "01"),
        (287, "02"),
        (431, "03"),
        (719, "04"),
        (1007, "05"),
        (1061, "06"),
        (1115, "07"),
        (1169, "08"),
        (1313, "09"),
        (1601, "10"),
        (1655, "11"),
        (1919, "12"),
        (2045, "13"),
        (2189, "14"),
        (2405, "15"),
        (2621, "16"),
        (2837, "17"),
        (3053, "18"),
        (3269, "19"),
        (3485, "20"),
        (3701, "21"),
        (3917, "22"),
        (4133, "23"),
        (4349, "24"),
        (4565, "25"),
        (4877, "26"),
        (5189, "27"),
        (5501, "28"),
        (5813, "29"),
        (6125, "30"),
        (6437, "31"),
        (6749, "32"),
        (7061, "33"),
        (7373, "34"),
        (7685, "35"),
        (7997, "36"),
        (8309, "37"),
        (8741, "38"),
        (9173, "39"),
        (9605, "40"),
    ]

    basket_id = "41"
    for limit, b_id in basket_ranges:
        if vol <= limit:
            basket_id = b_id
            break
    return f"https://basket-{basket_id}.wbbasket.ru/vol{vol}/part{part}/{article}"


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
