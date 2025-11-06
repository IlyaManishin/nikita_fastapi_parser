from typing import List
from pydantic import BaseModel
from concurrent import futures
import requests
import time
import logging
from google_sheets import get_wb_tokens

class ArticlePrice(BaseModel):
    nm_id: int
    discount: float
    price_retail: float
    discounted_price: float
    size: str
    
s_prices_data = []

def _get_token_prices_data(token: str) -> List[ArticlePrice]:
    headers = {"Authorization": token}
    limit = 1000
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
                time.sleep(7)

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


def _update_prices_task():
    global s_prices_data
    s_prices_data.clear()
    
    tokens = get_wb_tokens()
    if len(tokens) == 0:
        logging.error("No tokens error in prices update task")
        return

    with futures.ThreadPoolExecutor(max_workers=len(tokens)) as executor:
        all_futures = [executor.submit(
            _get_token_prices_data, token) for token in tokens]
        for future in futures.as_completed(all_futures):
            try:
                data = future.result()
                if data:
                    s_prices_data += data
            except Exception as err:
                logging.exception(err)
    logging.info(f"Fetched {len(s_prices_data)} articles")



def periodic_price_update():
    while True:
        try:
            _update_prices_task()
        except Exception as e:
            logging.exception(f"Error in periodic task: {e}")
        time.sleep(20 * 60)

def get_prices_data() -> List[ArticlePrice]:
    return s_prices_data

