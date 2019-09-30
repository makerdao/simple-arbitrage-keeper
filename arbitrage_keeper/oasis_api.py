import logging
import requests
from pymaker.util import http_response_summary



class OasisAPI:
    """A client for the Standard 0x Relayer API V2.
    <https://github.com/0xProject/standard-relayer-api/blob/master/http/v2.md>
    Attributes:
        exchange: The 0x Exchange V2 contract.
        api_server: Base URL of the Standard Relayer API server.
    """
    logger = logging.getLogger()
    timeout = 15.5

    def __init__(self, api_server: str):
        assert(isinstance(api_server, str))

        self.api_server = api_server


    def get_orders(self):
        """Returns active orders filtered by token pair (one side).
        In order to get them, issues a `/v2/orders` call to the Standard Relayer API.
        Args:

        Returns:

        """

        response = requests.get(f"{self.api_server}/v2/orders/{self.arb_token_name}/{self.sai_name}", timeout=self.timeout)
        if not response.ok:
            raise Exception(f"Failed to fetch 0x orders from the relayer: {http_response_summary(response)}")

        data = response.json()
        if 'data' in data:
            return data['data']['bids'], data['data']['asks']
        else:
            return []


    def __repr__(self):
        return f"OasisAPI()"
