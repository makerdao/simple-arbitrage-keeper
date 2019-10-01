# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017-2018 reverendus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import logging
import sys
import time
from typing import List

from web3 import Web3, HTTPProvider



from simple_arbitrage_keeper.uniswap import UniswapWrapper
from simple_arbitrage_keeper.oasis_api import OasisAPI
from simple_arbitrage_keeper.transfer_formatter import TransferFormatter

from pymaker import Address
from pymaker.approval import via_tx_manager, directly
from pymaker.gas import DefaultGasPrice, FixedGasPrice
from pymaker.keys import register_keys
from pymaker.lifecycle import Lifecycle
from pymaker.numeric import Wad, Ray
from pymaker.oasis import MatchingMarket
from pymaker.sai import Tub, Tap
from pymaker.token import ERC20Token
from pymaker.transactional import TxManager
from pymaker.zrx import ZrxExchange, ZrxRelayerApi


class SimpleArbitrageKeeper:
    """Keeper to arbitrage on OasisDEX and Uniswap"""

    logger = logging.getLogger('simple-arbitrage-keeper')

    def __init__(self, args, **kwargs):
        parser = argparse.ArgumentParser("simple-arbitrage-keeper")

        parser.add_argument("--rpc-host", type=str, default="localhost",
                            help="JSON-RPC host (default: `localhost')")

        parser.add_argument("--rpc-port", type=int, default=8545,
                            help="JSON-RPC port (default: `8545')")

        parser.add_argument("--rpc-timeout", type=int, default=10,
                            help="JSON-RPC timeout (in seconds, default: 10)")

        parser.add_argument("--eth-from", type=str, required=True,
                            help="Ethereum account from which to send transactions")

        parser.add_argument("--eth-key", type=str, nargs='*',
                            help="Ethereum private key(s) to use (e.g. 'key_file=aaa.json,pass_file=aaa.pass')")

        parser.add_argument("--uniswap-sai-address", type=str, required=True,
                            help="Ethereum address of the Uniswap Exchange contract for the SAI market")

        parser.add_argument("--uniswap-arb-address", type=str, required=True,
                            help="Ethereum address of the Uniswap Exchange contract for the arb token market")

        parser.add_argument("--oasis-address", type=str, required=True,
                            help="Ethereum address of the OasisDEX contract")

        parser.add_argument("--oasis-support-address", type=str, required=False,
                            help="Ethereum address of the OasisDEX support contract")

        parser.add_argument("--oasis-api-endpoint", type=str, required=True,
                            help="Address of the Oasis V2 REST API")

        parser.add_argument("--relayer-per-page", type=int, default=100,
                            help="Number of orders to fetch per one page from the 0x Relayer API (default: 100)")

        parser.add_argument("--tx-manager", type=str, required=True,
                            help="Ethereum address of the TxManager contract to use for multi-step arbitrage")

        parser.add_argument("--gas-price", type=int, default=0,
                            help="Gas price in Wei (default: node default)")

        parser.add_argument("--arb-token", type=str, required=True,
                            help="The token address that arbitraged between both exchanges")

        parser.add_argument("--arb-token-name", type=str, required=True,
                            help="The token name (e.g. MKR) that arbitraged between both exchanges")

        parser.add_argument("--min-profit", type=int, required=True,
                            help="Wei amount of minimum profit (in base token) from one arbitrage operation")

        parser.add_argument("--max-engagement", type=int, required=True,
                            help="Wei amount of maximum engagement (in base token) in one arbitrage operation")

        parser.add_argument("--max-errors", type=int, default=100,
                            help="Maximum number of allowed errors before the keeper terminates (default: 100)")

        parser.add_argument("--debug", dest='debug', action='store_true',
                            help="Enable debug output")

        self.arguments = parser.parse_args(args)

        self.web3 = kwargs['web3'] if 'web3' in kwargs else Web3(HTTPProvider(endpoint_uri=f"https://{self.arguments.rpc_host}:{self.arguments.rpc_port}",
                                                                              request_kwargs={"timeout": self.arguments.rpc_timeout}))
        self.web3.eth.defaultAccount = self.arguments.eth_from
        register_keys(self.web3, self.arguments.eth_key)
        self.our_address = Address(self.arguments.eth_from)


        self.sai = ERC20Token(web3=self.web3, address=Address('0xC4375B7De8af5a38a93548eb8453a498222C4fF2')) #SAI
        self.sai.name = "SAI"
        self.arb_token = ERC20Token(web3=self.web3, address=Address(self.arguments.arb_token)) #MKR, WETH or other
        self.arb_token.name = self.arguments.arb_token_name \
            if self.arguments.arb_token_name != 'WETH' else 'ETH'


        self.uniswap_sai_exchange = UniswapWrapper(self.web3, self.sai.address, Address(self.arguments.uniswap_sai_exchange)) \
            if self.arguments.exchange_address is not None else None

        self.uniswap_arb_exchange = UniswapWrapper(self.web3, self.arb_token.address, Address(self.arguments.uniswap_arb_exchange)) \
            if self.arguments.exchange_address is not None else None

        self.oasis_relayer_api = OasisAPI(self, api_server=self.arguments.oasis_api_endpoint) \
            if self.arguments.oasis_api_endpoint is not None else None

        self.oasis = MatchingMarket(web3=self.web3,
                                  address=Address(self.arguments.oasis_address),
                                  support_address=Address(self.arguments.oasis_support_address)
                                    if self.arguments.oasis_support_address is not None else None)


        self.min_profit = Wad.from_number(self.arguments.min_profit)
        self.max_engagement = Wad.from_number(self.arguments.max_engagement)
        self.max_errors = self.arguments.max_errors
        self.errors = 0

        if self.arguments.tx_manager:
            self.tx_manager = TxManager(web3=self.web3, address=Address(self.arguments.tx_manager))
            if self.tx_manager.owner() != self.our_address:
                raise Exception(f"The TxManager has to be owned by the address the keeper is operating from.")
        else:
            self.tx_manager = None

        logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s',
                            level=(logging.DEBUG if self.arguments.debug else logging.INFO))

    def main(self):
        with Lifecycle(self.web3) as lifecycle:
            self.lifecycle = lifecycle
            lifecycle.on_startup(self.startup)
            lifecycle.on_block(self.process_block)

    def startup(self):
        self.approve()

    def approve(self):
        """Approve all components that need to access our balances"""
        approval_method = via_tx_manager(self.tx_manager, gas_price=self.gas_price()) if self.tx_manager \
            else directly(gas_price=self.gas_price())

        self.oasis.approve([self.sai, self.arb_token], approval_method)

        if self.uniswap_sai_exchange:
            self.uniswap_sai_exchange.approve([self.sai], approval_method)

        if self.uniswap_arb_exchange:
            self.uniswap_arb_exchange.approve([self.arb_token], approval_method)

        if self.tx_manager:
            self.tx_manager.approve([self.sai, self.arb_token], directly(gas_price=self.gas_price()))


    #TODO: Check what units the oasis api results are in
    def oasis_order_size(self, size: Wad):
        if self.oasis_relayer_api is None:
            return None

        (bids, asks) = self.oasis_relayer_api.get_orders()

        sai_token_amount = 0
        arb_token_amount = 0

        if size is None:
            sai_token_amount = 0
            arb_token_amount = 0


            for order in asks:
                sai_token_amount = arb_token_amount + order[0] * order[1]
                arb_token_amount = arb_token_amount + order[1]

                if sai_token_amount >= self.entry_amount.value:
                    return Wad(arb_token_amount - order[0] + (sai_token_amount - self.entry_amount) * (1/order[0])) #some linear interpolation

        else:
            sai_token_amount = 0
            arb_token_amount = 0

            for order in bids:
                sai_token_amount = sai_token_amount + order[0] * order[1]
                arb_token_amount = arb_token_amount + order[1]

                if arb_token_amount >= size.value:
                    return Wad(sai_token_amount - (order[0] * order[1]) + (arb_token_amount - size) * (order[0])) #some linear interpolation

    def uniswap_order_size(self, size):
        if size is None:
            ethAmt = self.uniswap_sai_exchange.get_eth_token_output_price(self.entry_amount)
            arbAmt = self.uniswap_arb_amount.get_token_eth_output_price(ethAmt)
            return Wad(arbAmt)
        else:
            ethAmt = self.uniswap_arb_exchange.get_eth_token_output_price(size)
            saiAmt = self.uniswap_sai_exchange.get_token_eth_output_price(ethAmt)
            return Wad(saiAmt)


    def process_block(self):
        """Callback called on each new block.
        If too many errors, terminate the keeper to minimize potential damage."""
        if self.errors >= self.max_errors:
            self.lifecycle.terminate()
        else:
            self.find_best_opportunity_available()


    def find_best_opportunity_available(self):
        """Find the best arbitrage opportunity present and execute it."""

        self.entry_amount = Wad.min(self.sai_token.balance_of(self.our_address), self.max_engagement)

        oasis_arb_amount = oasis_order_size()
        profit_oasis_to_uniswap = uniswap_order_size(oasis_arb_amount) - self.entry_amount

        uniswap_arb_amount = uniswap_order_size()
        profit_uniswap_to_oasis = oasis_order_size(uniswap_arb_amount) - self.entry_amount

        if profit_oasis_to_uniswap > profit_uniswap_to_oasis:
            self.start_exchange, self.start_exchange.name, self.arb_amount = self.oasis, 'Oasis', Wad(oasis_arb_amount)
            self.end_exchange, self.end_exchange.name = self.uniswap_arb_exchange, 'Uniswap'

        else:
            self.start_exchange, self.start_exchange.name, self.arb_amount = self.uniswap_sai_exchange, 'Uniswap', Wad(uniswap_arb_amount)
            self.end_exchange, self.end_exchange.name = self.oasis, 'Oasis'

        highestProfit = max(profit_oasis_to_uniswap, profit_uniswap_to_oasis)
        self.exit_amount = highestProfit + self.entry_amount

        print(highestProfit.value)

        opportunity = highestProfit if highestProfit > self.min_profit else None

        # TODO uncomment this when ready to test transactions
        # if opportunity:
        #     self.print_opportunity(opportunity)
        #     self.execute_opportunity_in_one_transaction()


    def print_opportunity(self, opportunity: Wad):
        """Print the details of the opportunity."""
        self.logger.info(f"Profit opportunity of {oppportunity.value} from {self.start_exchange.name} to {self.end_exchange.name}")


    # TODO: Figure out how to specify invocation for both Uniswap and Oasis order book
    def execute_opportunity_in_one_transaction(self, opportunity: Wad):
        """Execute the opportunity in one transaction, using the `tx_manager`."""

        tokens = [self.sai.address, self.arb_token.address]

        invocations = [self.start_echange.make(pay_token=self.sai.address,
                                               pay_amount=self.entry_amount,
                                               buy_token=self.arb_token.address,
                                               buy_amount=self.arb_amount).invocation(),
                       self.end_exchange.make(pay_token=self.arb_token.address,
                                               pay_amount=self.arb_amount,
                                               buy_token=self.sai.address,
                                               buy_amount=self.exit_amount).invocation()]

        receipt = self.tx_manager.execute(tokens, invocations).transact(gas_price=self.gas_price())

        if receipt:
            self.logger.info(f"The profit we made is {TransferFormatter().format_net(receipt.transfers, self.our_address, self.sai.name)}")
        else:
            self.errors += 1


    def gas_price(self):
        if self.arguments.gas_price > 0:
            return FixedGasPrice(self.arguments.gas_price)
        else:
            return DefaultGasPrice()


if __name__ == '__main__':
    SimpleArbitrageKeeper(sys.argv[1:]).main()
