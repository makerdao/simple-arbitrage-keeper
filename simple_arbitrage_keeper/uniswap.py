from pymaker import Transact, Address
from pyexchange.uniswap import Uniswap

from web3 import Web3
from typing import List
from pymaker.token import ERC20Token
from pymaker.numeric import Wad



class UniswapWrapper:
    """ Uniswap Wrapper, used to expose approve(), make(), and other function headers. """
    def __init__(self, web3: Web3, token: Address, exchange: Address):

        self.uniswap_base = Uniswap(web3, token, exchange)
        self.address = exchange

    def approve(self, tokens: List[ERC20Token], approval_function):
        """Approve the Uniswap contract to fully access balances of specified tokens.

        For available approval functions (i.e. approval modes) see `directly` and `via_tx_manager`
        in `pymaker.approval`.

        Args:
            tokens: List of :py:class:`pymaker.token.ERC20Token` class instances.
            approval_function: Approval function (i.e. approval mode).
        """
        assert(isinstance(tokens, list))
        assert(callable(approval_function))

        for token in tokens:
            approval_function(token, self.address, 'Uniswap')


    def make(self, pay_token: Address, pay_amount: Wad, buy_token: Address, buy_amount: Wad) -> Transact:
        """ Wrapper for Uniswap exchange tokens->tokens swap method

        The `pay_amount` of `pay_token` token will be taken from you and swapped for atleast the `buy_amount`
        of `buy_token` through the Uniswap exchange contracts for both tokens. Allowance for the `pay_token` needs to be set first.
        Refer to the `approve()` method in the `ERC20Token` class in github.com/makerdao/pymaker

        Uniswap tokensToTokenSwapInput API: https://docs.uniswap.io/smart-contract-api/exchange#tokentotokenswapinput

        Args:
            pay_token: Address of the ERC20 token you want to swap.
            pay_amount: Amount of the `pay_token` you want to swap.
            buy_token: Address of the ERC20 token you want to recieve.
            buy_amount: Amount of the `buy_token` you want to receive.

        Returns:
            A :py:class:`pymaker.Transact` instance, which can be used to trigger the transaction.
        """

        assert(isinstance(pay_token, Address))
        assert(isinstance(pay_amount, Wad))
        assert(isinstance(buy_token, Address))
        assert(isinstance(buy_amount, Wad))
        assert(pay_amount > Wad(0))
        assert(buy_amount > Wad(0))


        return Transact(self, self.uniswap_base.web3, self.uniswap_base.abi, self.uniswap_base.exchange, self.uniswap_base._contract,
                        'tokenToTokenSwapInput', [pay_amount.value, buy_amount.value, 1, self.uniswap_base._deadline(), buy_token.address])
