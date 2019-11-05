import logging
import requests
from pymaker.util import http_response_summary



class OasisAPI:
    """A class for reading and presenting json data from the Oasis Rest API

    Documentation: developer.makerdao.com/oasis/api/2/markets

    """
    logger = logging.getLogger()
    timeout = 15.5

    def __init__(self, api_server: str, entry_token_name: str, arb_token_name: str):
        assert(isinstance(api_server, str))


        self.entry_token_name = entry_token_name
        self.arb_token_name = arb_token_name
        self.api_server = api_server


    def get_orders(self):
        """Returns active orders filtered by token pair
        Issues an `/v2/orders/XYZ/XYZ` call to the Oasis REST API

        Returns:
            Two lists: bid elements [price (float), amount (float)] and ask elements [price (float), amounts (float)]
        """

        response = requests.get(f"{self.api_server}/v2/orders/{self.arb_token_name}/{self.entry_token_name}", timeout=self.timeout)
        if not response.ok:
            raise Exception(f"Failed to fetch Oasis orders from REST API: {http_response_summary(response)}")

        data = response.json()
        if 'data' in data:
            bids = list(map(lambda x: [float(i) for i in x], data['data']['bids']))
            asks = list(map(lambda x: [float(i) for i in x], data['data']['asks']))
            return bids, asks

        else:
            return []
