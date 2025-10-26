from typing import List
from pydantic import BaseModel
from concurrent import futures
import requests
import time
import json
import logging


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


class ArticlePrice(BaseModel):
    nm_id: int
    discount: float
    price_retail: float
    discounted_price: float
    size: str


def get_basket(article: int) -> str:
    vol = int(article / 100000)
    part = int(article / 1000)

    if vol <= 143:
        basket = f"https://basket-01.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 287:
        basket = f"https://basket-02.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 431:
        basket = f"https://basket-03.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 719:
        basket = f"https://basket-04.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1007:
        basket = f"https://basket-05.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1061:
        basket = f"https://basket-06.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1115:
        basket = f"https://basket-07.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1169:
        basket = f"https://basket-08.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1313:
        basket = f"https://basket-09.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1601:
        basket = f"https://basket-10.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1655:
        basket = f"https://basket-11.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 1919:
        basket = f"https://basket-12.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 2045:
        basket = f"https://basket-13.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 2189:
        basket = f"https://basket-14.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 2405:
        basket = f"https://basket-15.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 2621:
        basket = f"https://basket-16.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 2837:
        basket = f"https://basket-17.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 3053:
        basket = f"https://basket-18.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 3269:
        basket = f"https://basket-19.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 3485:
        basket = f"https://basket-20.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 3701:
        basket = f"https://basket-21.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 3917:
        basket = f"https://basket-22.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 4133:
        basket = f"https://basket-23.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 4349:
        basket = f"https://basket-24.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 4565:
        basket = f"https://basket-25.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 4877:
        basket = f"https://basket-26.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 5189:
        basket = f"https://basket-27.wbbasket.ru/vol{vol}/part{part}/{article}"
    elif vol <= 5501:
        basket = f"https://basket-28.wbbasket.ru/vol{vol}/part{part}/{article}"
    else:
        basket = f"https://basket-29.wbbasket.ru/vol{vol}/part{part}/{article}"

    return basket


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


def get_prices_data(token: str) -> List[ArticlePrice]:
    headers = {"Authorization": token}
    limit = 500
    offset = 0
    all_list_goods = []

    while True:
        tryings = 3
        resp_data = None
        for _ in range(tryings):
            try:
                url = f"https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter?limit={limit}&offset={offset}"
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                resp_data = resp.json()["data"]["listGoods"]
                break
            except Exception:
                pass
            finally:
                time.sleep(10)

        if not resp_data:
            break

        all_list_goods += resp_data
        if len(resp_data) < limit:
            break
        offset += limit

    result: List[ArticlePrice] = []

    for item in all_list_goods:
        nm_id = item["nmID"]
        discount = item.get("discount", 0)
        price_retail = 0
        discounted_price = 0
        size_name = ""
        if item.get("sizes"):
            size = item["sizes"][0]
            size_name = size.get("techSizeName", "")
            price_retail = size.get("price", 0)
            discounted_price = size.get("discountedPrice", 0)

        article_price = ArticlePrice(
            nm_id=nm_id,
            discount=discount,
            price_retail=price_retail,
            discounted_price=discounted_price,
            size=size_name
        )
        result.append(article_price)

    return result


def get_products(articles: List[int], token) -> List[Product]:
    all_data = []
    prices_data = get_prices_data(token)
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
