import requests
import time
import json
from enum import Enum
from typing import Union
import logging


REQUEST_ATTEMPT_COUNT = 3
REQUEST_WAIT_SEC = 5


class UnathorizedExc(Exception):
    pass


class InvalidBodyExc(Exception):
    pass


class RequestTypes(Enum):
    GET = "GET"
    POST = "POST"


def get_auth_header(token: str) -> dict:
    header = {"Authorization": token}
    return header


def _send_request(url: str,
                  headers: dict,
                  attempts: int,
                  on_error_wait_sec: int,
                  mode: RequestTypes,
                  body: dict = None) -> Union[list[dict], dict]:
    resp = None
    for i in range(attempts):
        try:
            if mode == RequestTypes.GET:
                resp = requests.get(url, headers=headers,
                                    timeout=on_error_wait_sec)
            elif mode == RequestTypes.POST:
                if body is None:
                    body = {}
                resp = requests.post(url, headers=headers,
                                     json=body, timeout=on_error_wait_sec)
            if resp.status_code != 200:
                logging.error(
                    f"Api error (status={resp.status_code}) resp = {resp.text}, url = {url}")
            if resp.status_code == 401:
                raise UnathorizedExc()
            if resp.status_code != 200:
                raise Exception(f"Request error, status: {resp.status_code}")

            data = json.loads(resp.text)
            return data
        except UnathorizedExc as err:
            raise
        except Exception as err:
            if resp and resp.status_code == 429:
                time.sleep(on_error_wait_sec)
                continue
            logging.exception(err)
    raise Exception(
        f"Invalid request: url={url}" + f", status={resp.status_code}" if resp else "")


def api_get(url: str, headers: dict,
            attempts: int = REQUEST_ATTEMPT_COUNT,
            req_wait_sec=REQUEST_WAIT_SEC) -> Union[list[dict], dict]:
    return _send_request(url, headers, attempts, req_wait_sec, RequestTypes.GET)


def api_post(url: str, headers: dict, body: dict,
             attempts: int = REQUEST_ATTEMPT_COUNT,
             req_wait_sec=REQUEST_WAIT_SEC) -> Union[list[dict], dict]:
    return _send_request(url, headers, attempts, req_wait_sec, RequestTypes.POST, body)

