import logging
import requests
from pymaker.util import http_response_summary



class OasisAPI:
    """A class for reading and presenting json data from the Oasis Rest API

    Documentation: developer.makerdao.com/oasis/api/v2

    """
    logger = logging.getLogger()
    timeout = 15.5

    def __init__(self, api_server: str):
        assert(isinstance(api_server, str))

        self.api_server = api_server


    def get_orders(self):
        """Returns active orders filtered by token pair
        In order to get them, issues an `/v2/orders/XYZ/XYZ` call to the Oasis REST API

        Returns: List of bid elements [price (float), amount (float)] and ask elements [price (float), amounts (float)]

        """

        response = requests.get(f"{self.api_server}/v2/orders/{self.arb_token.name}/{self.sai.name}", timeout=self.timeout)
        if not response.ok:
            raise Exception(f"Failed to fetch Oasis orders from REST API: {http_response_summary(response)}")

        data = response.json()
        if 'data' in data:
            return data['data']['bids'], data['data']['asks']
        else:
            return []


    def __repr__(self):
        return f"OasisAPI()"
