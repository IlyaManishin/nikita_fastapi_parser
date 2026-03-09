import logging
from dataclasses import dataclass
from typing import List
from . import utils


CARDS_LIST_URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"
CARDS_WAIT_TIME = 15


@dataclass
class Article:
    nm_id: int
    brand: str
    desc: str
    vendor: str
    name: str
    tech_size: str
    chrt_id: int
    height: int
    width: int
    length: int
    unit: str
    weight: int
    category: str


def card_to_articles(card) -> List[Article]:
    nm_id = card.get("nmID", 0)
    if not nm_id:
        return []

    brand = card.get("brand", "")
    desc = card.get("description", "")
    vendor = card.get("vendorCode", "")
    name = card.get("title", "")
    dims = card.get("dimensions", {})
    height = dims.get("height", 0)
    width = dims.get("width", 0)
    length = dims.get("length", 0)
    category = card.get("subjectName", "")

    weight = 0
    for c in card.get("characteristics", []):
        if not c:
            continue
        k, v = next(iter(c.items()))
        if "Вес с упаковкой" in k:
            weight = v

    result = []
    for size in card.get("sizes", []):
        result.append(
            Article(
                nm_id=nm_id,
                brand=brand,
                desc=desc,
                vendor=vendor,
                name=name,
                tech_size=size.get("techSize", ""),
                chrt_id=size.get("chrtID", 0),
                height=height,
                width=width,
                length=length,
                unit="см",
                weight=weight,
                category=category,
            )
        )
    return result


def get_articles_by_token(token: str) -> List[Article]:
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    payload = {
        "settings": {
            "cursor": {"limit": 100},
            "filter": {"withPhoto": -1},
        }
    }

    all_cards = []
    is_end = False

    while not is_end:
        try:
            resp = utils.api_post(
                CARDS_LIST_URL,
                headers=headers,
                body=payload,
                attempts=5,
                req_wait_sec=CARDS_WAIT_TIME
            )
        except Exception as err:
            logging.exception(err)
            return []

        if not resp:
            logging.error(
                f"No articles data for token: ...{token[len(token) - 20:]}")
            return []

        all_cards.extend(resp["cards"])
        cursor = resp["cursor"]
        if cursor["total"] < 100:
            is_end = True
        else:
            payload["settings"]["cursor"]["updatedAt"] = cursor["updatedAt"]
            payload["settings"]["cursor"]["nmID"] = cursor["nmID"]

    articles: List[Article] = []

    for card in all_cards:
        articles.extend(card_to_articles(card))

    return articles
