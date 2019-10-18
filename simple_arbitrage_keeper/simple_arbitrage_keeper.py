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

from web3 import Web3, HTTPProvider



from simple_arbitrage_keeper.uniswap import UniswapWrapper
from simple_arbitrage_keeper.oasis_api import OasisAPI
from simple_arbitrage_keeper.transfer_formatter import TransferFormatter

from pymaker import Address
from pymaker.approval import via_tx_manager, directly
from pymaker.gas import DefaultGasPrice, FixedGasPrice
from pymaker.keys import register_keys
from pymaker.lifecycle import Lifecycle
from pymaker.numeric import Wad
from pymaker.oasis import MatchingMarket
from pymaker.token import ERC20Token
from pymaker.transactional import TxManager


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
                            help="Ethereum address from which to send transactions; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--eth-key", type=str, nargs='*', required=True,
                            help="Ethereum private key(s) to use (e.g. 'key_file=/path/to/keystore.json,pass_file=/path/to/passphrase.txt')")

        parser.add_argument("--uniswap-entry-exchange", type=str, required=True,
                            help="Ethereum address of the Uniswap Exchange contract for the entry token market; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--uniswap-arb-exchange", type=str, required=True,
                            help="Ethereum address of the Uniswap Exchange contract for the arb token market; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--oasis-address", type=str, required=True,
                            help="Ethereum address of the OasisDEX contract; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--oasis-api-endpoint", type=str, required=True,
                            help="Address of the Oasis V2 REST API; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--relayer-per-page", type=int, default=100,
                            help="Number of orders to fetch per one page from the 0x Relayer API (default: 100)")

        parser.add_argument("--tx-manager", type=str, required=True,
                            help="Ethereum address of the TxManager contract to use for multi-step arbitrage; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--gas-price", type=int, default=0,
                            help="Gas price in Wei (default: node default), (e.g. 1000000000 for 1 GWei)")

        parser.add_argument("--entry-token", type=str, required=True,
                            help="The token address that the bot starts and ends with in every transaction; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--arb-token", type=str, required=True,
                            help="The token address that arbitraged between both exchanges; checksummed (e.g. '0x12AebC')")

        parser.add_argument("--arb-token-name", type=str, required=True,
                            help="The token name that arbitraged between both exchanges (e.g. 'SAI', 'WETH', 'REP')")

        parser.add_argument("--min-profit", type=int, required=True,
                            help="Ether amount of minimum profit (in base token) from one arbitrage operation (e.g. 1 for 1 Sai min profit)")

        parser.add_argument("--max-engagement", type=int, required=True,
                            help="Ether amount of maximum engagement (in base token) in one arbitrage operation (e.g. 100 for 100 Sai max engagement)")

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

        self.sai = ERC20Token(web3=self.web3, address=Address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'))

        self.entry_token = ERC20Token(web3=self.web3, address=Address(self.arguments.entry_token))
        self.arb_token = ERC20Token(web3=self.web3, address=Address(self.arguments.arb_token))
        self.arb_token.name = self.arguments.arb_token_name \
            if self.arguments.arb_token_name != 'WETH' else 'ETH'


        self.uniswap_entry_exchange = UniswapWrapper(self.web3, self.entry_token.address, Address(self.arguments.uniswap_entry_exchange)) \
            if self.arguments.uniswap_entry_exchange is not None else None

        self.uniswap_arb_exchange = UniswapWrapper(self.web3, self.arb_token.address, Address(self.arguments.uniswap_arb_exchange)) \
            if self.arguments.uniswap_arb_exchange is not None else None

        self.oasis_api_endpoint = OasisAPI(api_server=self.arguments.oasis_api_endpoint,
                                           entry_token_name=self.token_name(self.entry_token.address),
                                           arb_token_name=self.arb_token.name) \
            if self.arguments.oasis_api_endpoint is not None else None

        self.oasis = MatchingMarket(web3=self.web3, address=Address(self.arguments.oasis_address))


        self.min_profit = Wad(int(self.arguments.min_profit * 10**18))
        self.max_engagement = Wad(int(self.arguments.max_engagement * 10**18))
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

        self.oasis.approve([self.entry_token, self.arb_token], approval_method)

        if self.uniswap_entry_exchange:
            self.uniswap_entry_exchange.approve([self.entry_token], approval_method)

        if self.uniswap_arb_exchange:
            self.uniswap_arb_exchange.approve([self.arb_token], approval_method)

        if self.tx_manager:
            self.tx_manager.approve([self.entry_token, self.arb_token], directly(gas_price=self.gas_price()))


    def token_name(self, address: Address) -> str:
        if address == self.sai.address:
            return "DAI"
        else:
            return str(address)

    def oasis_order_size(self, size: Wad = None):
        if self.oasis_api_endpoint is None:
            return None

        (bids, asks) = self.oasis_api_endpoint.get_orders()

        entry_token_amount = 0
        arb_token_amount = 0

        if size is None:
            for order in asks:
                entry_token_amount = entry_token_amount + order[0] * order[1]
                arb_token_amount = arb_token_amount + order[1]

                if entry_token_amount >= float(self.entry_amount):
                    #some linear interpolation
                    final_arb_token_amount = arb_token_amount - order[1] + \
                        (float(self.entry_amount) - (entry_token_amount - order[0] * order[1])) * (1/order[0])
                    return Wad(int(final_arb_token_amount*10**18))

        else:
            for order in bids:
                entry_token_amount = entry_token_amount + order[0] * order[1]
                arb_token_amount = arb_token_amount + order[1]

                if arb_token_amount >= float(size):
                    #some linear interpolation
                    final_entry_token_amount = entry_token_amount - (order[0] * order[1]) + \
                        (float(size) - (arb_token_amount - order[1])) * (order[0])
                    return Wad(int(final_entry_token_amount*10**18))


    def uniswap_order_size(self, size: Wad = None):
        if size is None:
            ethAmt = self.uniswap_entry_exchange.uniswap_base.get_token_eth_input_price(self.entry_amount)
            arbAmt = self.uniswap_arb_exchange.uniswap_base.get_eth_token_input_price(ethAmt)
            return Wad(arbAmt)
        else:
            ethAmt = self.uniswap_arb_exchange.uniswap_base.get_token_eth_input_price(size)
            entryAmt = self.uniswap_entry_exchange.uniswap_base.get_eth_token_input_price(ethAmt)
            return Wad(entryAmt)


    def process_block(self):
        """Callback called on each new block.
        If too many errors, terminate the keeper to minimize potential damage."""
        if self.errors >= self.max_errors:
            self.lifecycle.terminate()
        else:
            self.find_best_opportunity_available()


    def find_best_opportunity_available(self):
        """Find the best arbitrage opportunity present and execute it."""

        self.entry_amount = Wad.min(self.entry_token.balance_of(self.our_address), self.max_engagement)

        oasis_arb_amount = self.oasis_order_size()
        profit_oasis_to_uniswap = self.uniswap_order_size(oasis_arb_amount) - self.entry_amount

        uniswap_arb_amount = self.uniswap_order_size()
        profit_uniswap_to_oasis = self.oasis_order_size(uniswap_arb_amount) - self.entry_amount

        if profit_oasis_to_uniswap > profit_uniswap_to_oasis:
            self.start_exchange, self.start_exchange.name = self.oasis, 'Oasis'
            self.arb_amount = oasis_arb_amount * Wad.from_number(0.999999)
            self.end_exchange, self.end_exchange.name = self.uniswap_arb_exchange, 'Uniswap'

        else:
            self.start_exchange, self.start_exchange.name = self.uniswap_entry_exchange, 'Uniswap'
            self.arb_amount = uniswap_arb_amount * Wad.from_number(0.999999)
            self.end_exchange, self.end_exchange.name = self.oasis, 'Oasis'

        highestProfit = max(profit_oasis_to_uniswap, profit_uniswap_to_oasis)
        self.exit_amount = (highestProfit + self.entry_amount) * Wad.from_number(0.999999)

        #Print the highest profit/(loss) to see how close we come to breaking even
        self.logger.info(f"Best trade regardless of profit/min-profit: {highestProfit} {self.token_name(self.entry_token.address)} "
                         f"from {self.start_exchange.name} to {self.end_exchange.name}")

        opportunity = highestProfit if highestProfit > self.min_profit else None

        if opportunity:
            self.print_opportunity(opportunity)
            self.execute_opportunity_in_one_transaction()




    def print_opportunity(self, opportunity: Wad):
        """Print the details of the opportunity."""
        self.logger.info(f"Profit opportunity of {opportunity} {self.token_name(self.entry_token.address)} "
                         f"from {self.start_exchange.name} to {self.end_exchange.name}")


    def execute_opportunity_in_one_transaction(self):
        """Execute the opportunity in one transaction, using the `tx_manager`."""

        tokens = [self.entry_token.address, self.arb_token.address]

        invocations = [self.start_exchange.make(pay_token=self.entry_token.address,
                                               pay_amount=self.entry_amount,
                                               buy_token=self.arb_token.address,
                                               buy_amount=self.arb_amount).invocation(),
                       self.end_exchange.make(pay_token=self.arb_token.address,
                                               pay_amount=self.arb_amount,
                                               buy_token=self.entry_token.address,
                                               buy_amount=self.exit_amount).invocation()]

        receipt = self.tx_manager.execute(tokens, invocations).transact(gas_price=self.gas_price(), gas_buffer=300000)

        if receipt:
            self.logger.info(f"The profit we made is {TransferFormatter().format_net(receipt.transfers, self.our_address, self.token_name)}")
        else:
            self.errors += 1


    def gas_price(self):
        if self.arguments.gas_price > 0:
            return FixedGasPrice(self.arguments.gas_price)
        else:
            return DefaultGasPrice()


if __name__ == '__main__':
    SimpleArbitrageKeeper(sys.argv[1:]).main()
