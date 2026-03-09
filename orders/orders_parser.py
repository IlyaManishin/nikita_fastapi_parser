import logging
from datetime import datetime, timedelta, date
from pydantic import BaseModel
import time
from dataclasses import dataclass

from google_sheets import service, get_wb_tokens, spreadsheets_id, ensure_sheet_exists
import orders.articles as articles
from orders.articles import Article
from . import utils

SALES_STATS_URL = "https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products"
SALES_URL = "https://statistics-api.wildberries.ru/api/v1/supplier/sales"
SALES_PERIOD_DAYS = 30
DIFF_DAYS_COUNT = 10

PERIOD_SEC = 60 * 60 * 24


@dataclass
class _RunConfig:
    sheets_id: str
    token: str
    task_id: int
    diff_days_count: int
    is_debug: bool


class SalesStat(BaseModel):
    article: int
    seller_article: str
    brand: str
    category: str
    month_sales: int
    cur_stocks: int
    middle_in_day_sales: float
    month_income: int
    no_available_days: int

    days_stats: list[int]

    saleRate: int
    availability: str


class Sale(BaseModel):
    article: int
    date: date


def get_period_stats(token: str, articles: list[int], start: datetime, end: datetime) -> list[dict]:
    all_items = []
    limit = 1000

    for i in range(0, len(articles), limit):
        batch = articles[i:i + limit]

        body = {
            "nmIDs": batch,
            "currentPeriod": {
                "start": start.strftime(r"%Y-%m-%d"),
                "end": end.strftime(r"%Y-%m-%d")
            },
            "stockType": "",
            "skipDeletedNm": True,
            "orderBy": {
                "field": "ordersCount",
                "mode": "asc"
            },
            "availabilityFilters": [
                # "deficient",
                # "actual",
                # "balanced",
                # "nonActual",
                # "nonLiquid",
                # "invalidData",
            ],
            "limit": limit,
            "offset": 0
        }

        headers = utils.get_auth_header(token)
        try:
            result = utils.api_post(SALES_STATS_URL,
                                    headers, body, req_wait_sec=20)
        except Exception as err:
            logging.exception(err)
            break
        time.sleep(20)

        items = result.get("data", {}).get("items", [])
        if not items:
            break
        all_items += items

    return all_items


def get_period_sales(token: str, start_date: datetime) -> list[Sale]:
    header = utils.get_auth_header(token)
    url_time = start_date.strftime(r"%Y-%m-%d")
    url = f"{SALES_URL}?dateFrom={url_time}"

    try:
        resp = utils.api_get(url, header, 5)
        if not resp:
            raise Exception("No resp data")
    except Exception as err:
        logging.exception(err)
        return []

    res = []
    for i in resp:
        if "nmId" not in i:
            continue
        entry = Sale(
            article=i.get("nmId", 0),
            date=datetime.strptime(
                i.get("date", "1970-01-01T00:00:00"), r"%Y-%m-%dT%H:%M:%S").date(),
        )
        res.append(entry)
    return res


def read_sales_stats(token, config: _RunConfig,  articles_data: list[Article]) -> list[SalesStat]:
    articles = [i.nm_id for i in articles_data]
    now = datetime.now()

    end_date = now - timedelta(days=1)
    start_date = end_date - timedelta(days=config.diff_days_count - 1)

    month_stats = get_period_stats(token, articles, start_date, end_date)
    if not month_stats:
        return None

    today_stocks: dict[int, int] = {}
    month_data = {}
    for item in month_stats:
        article = item["nmID"]
        metrics = item.get("metrics", {})

        month_sales = metrics.get("ordersCount", 0)
        avg_sales = metrics.get("avgOrders", 0)
        period_income = metrics.get("ordersSum", 0)
        not_available = metrics.get("officeMissingTime", {}).get("days", 30)

        stocks = metrics.get("stockCount", 0)
        today_stocks[article] = stocks

        month_data[article] = dict(
            month_sales=month_sales,
            middle_in_day_sales=avg_sales,
            month_income=period_income,
            no_available_days=not_available,
            saleRate=metrics.get("saleRate", {}).get("days", 0),
            availability=metrics.get("availability", "")
        )

    date_range = [(start_date + timedelta(days=d))
                  for d in range(config.diff_days_count)]
    article_daily_data = {a: {} for a in articles}

    for day in date_range:
        day_stats = get_period_stats(token, articles, day, day)
        if not day_stats:
            continue

        for item in day_stats:
            article = item["nmID"]
            metrics = item.get("metrics", {})
            if not metrics:
                continue
            orders = metrics.get("ordersCount", 0)
            if article in article_daily_data:
                article_daily_data[article][day.date()] = orders

    sales_stats = []
    for art_data in articles_data:
        article = art_data.nm_id
        mdata = month_data.get(article, {})

        days_stats = []
        for day in date_range:
            sales_count = article_daily_data.get(
                article, {}).get(day.date(), 0)
            days_stats.append(sales_count)

        sales_stats.append(SalesStat(
            article=article,
            seller_article=art_data.vendor,
            brand=art_data.brand,
            category=art_data.category,
            month_sales=mdata.get("month_sales", 0),
            cur_stocks=today_stocks.get(article, 0),
            middle_in_day_sales=mdata.get("middle_in_day_sales", 0.0),
            month_income=mdata.get("month_income", 0),
            no_available_days=mdata.get("no_available_days", 0),
            days_stats=days_stats,
            saleRate=mdata.get("saleRate", 0),
            availability=mdata.get("availability", "")
        ))

    return sales_stats


def convert_sales_stats_to_table(rconfig: _RunConfig,
                                 articles_data: list[Article],
                                 stats: list[SalesStat]) -> list[list]:
    base_columns = ["Артикул WB", "Артикул поставщика", "Бренд", "Категория",
                    "Всего продаж за месяц", "Остаток", "Среднее количество заказов в день",
                    "Выручка за 30 дней (руб)", "Товара нет в наличии (дней)"]

    data = []
    data.append(["", "Дата обновления:",
                datetime.now().strftime(r"%Y-%m-%d %H:%M")])
    header_up = [""] * len(base_columns)
    for i in range(rconfig.diff_days_count, 0, -1):
        header_up += [f"{i} д. назад"]
    data.append(header_up)

    header_down = []
    header_down += base_columns
    for i in range(rconfig.diff_days_count):
        header_down += ["Заказы"]
    data.append(header_down)

    article_res = {}
    for i in stats:
        article_res[i.article] = i

    for i in articles_data:
        article = i.nm_id
        if article not in article_res:
            data.append([])
        else:
            row = []
            stat: SalesStat = article_res[article]

            row.append(stat.article)
            row.append(stat.seller_article)
            row.append(stat.brand)
            row.append(stat.category)
            row.append(stat.month_sales)
            row.append(stat.cur_stocks)
            row.append(stat.middle_in_day_sales)
            row.append(stat.month_income)
            row.append(stat.no_available_days)

            for day_stat in stat.days_stats:
                row.append(day_stat)

            data.append(row)

    return data


def save_sales_stats_to_sheet(spreadsheet_id: str, sheet_name: str, data: list[list]):
    ensure_sheet_exists(spreadsheet_id, sheet_name)

    range_name = f"{sheet_name}!A:ZZ"
    body = {
        "values": data
    }

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=sheet_name
    ).execute()

    tryings = 3
    is_valid = False
    for _ in range(tryings):
        try:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
            is_valid = True
            break
        except:
            pass
    if not is_valid:
        logging.error("Google sheets access error")


def _period_sales_task_internal(rconfig: _RunConfig):
    token = rconfig.token
    articles_data: list[Article] = articles.get_articles_by_token(token)

    if not articles_data:
        logging.error(
            f"No articles data from token: ...{token[len(token) - 20:]}")
        return
    stats = read_sales_stats(token, rconfig, articles_data)
    if not stats:
        logging.error(
            f"Can't get stats from token: ...{token[len(token) - 20:]}")
        return
    google_data = convert_sales_stats_to_table(rconfig, articles_data, stats)
    sheet_name = f"Токен №{rconfig.task_id}"
    save_sales_stats_to_sheet(rconfig.sheets_id, sheet_name, google_data)


def period_sales_task():
    tokens = get_wb_tokens()
    if not tokens:
        logging.error("No tokensin orders_parser")
        return

    for index, token in enumerate(tokens, start=1):
        rconfig = _RunConfig(spreadsheets_id, token,
                             index, DIFF_DAYS_COUNT, False)
        _period_sales_task_internal(rconfig)


def period_sales_scheduler():
    while True:
        now = datetime.now()
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)

        if now >= target:
            target += timedelta(days=1)

        sleep_sec = (target - now).total_seconds()
        time.sleep(sleep_sec)

        try:
            period_sales_task()
        except Exception as err:
            logging.exception(f"period_sales_task failed: {err}")
