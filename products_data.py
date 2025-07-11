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
    price: int


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

def get_photo_url(article: int) -> str:
    basket = get_basket(article)
    url = f"{basket}/images/big/1.webp"
    photo_url = f'=ARRAYFORMULA(IMAGE("{url}"))'
    return photo_url

def _get_product_data(article: int, wallet_percent: int) -> Product:
    tryings = 5
    data = None
    is_valid = False
    product = None
    for i in range(tryings):
        status = None
        try:
            url = f'https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257218&spp=30&nm={article}'
            resp = requests.get(url)
            status = resp.status_code
            if status != 200:
                raise Exception()
            text = resp.text
            data = json.loads(text)
            product_data: dict = data['data']['products'][0]
            is_valid = True
            break
        except:
            if status == 200:
                break
            time.sleep(10)

    photo_url = get_photo_url(article)
    if not is_valid:
        product = Product(article=article,
                          photo_url=photo_url,
                          category="-",
                          seller_name="-",
                          url=f"https://www.wildberries.ru/catalog/{article}/detail.aspx",
                          price=0)
        return product

    product = Product(article=article,
                      photo_url=photo_url,
                      category=product_data.get("name", ""),
                      seller_name=product_data.get("supplier", ""),
                      url=f"https://www.wildberries.ru/catalog/{article}/detail.aspx",
                      price=0)
    sizes = product_data.get("sizes", [])
    if len(sizes) > 0:
        size = sizes[0]
        price = size.get("price", {}).get("product", 0) // 100
        wallet_price = price * (100 - wallet_percent) // 100
        product.price = wallet_price
    return product


def _get_product_task(article: int, *args):
    try:
        res = _get_product_data(article, *args)
        return res
    except Exception as err:
        logging.error(f"Article error: {article}")
        logging.exception(err)
    return


def get_products(articles: List[int], wallet_percent: int = 2) -> List[Product]:
    all_data = []
    with futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        all_futures = []
        for article in articles:
            all_futures.append(executor.submit(
                _get_product_task, article, wallet_percent))
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
    result = [get_photo_url(article) for article in articles]
    return result