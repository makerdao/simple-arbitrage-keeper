from pymaker import Transact, Address
from pyexchange.uniswap import Uniswap

from web3 import Web3
from typing import List
from pymaker.token import ERC20Token
from pymaker.numeric import Wad



class UniswapWrapper:
    """ Uniswap Wrapper, used to expose approve(), make(), and other function headers.

    """
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
        """
        Wrapper for Uniswap exchange tokens->tokens swap method

        The `have_amount` of `have_token` token will be taken from you on order creation and deposited
        in the market contract. Allowance needs to be set first. Refer to the `approve()` method
        in the `ERC20Token` class in github.com/makerdao/pymaker

        Args:
            pay_token: Address of the ERC20 token you want to put on sale.
            pay_amount: Amount of the `pay_token` token you want to put on sale.
            buy_token: Address of the ERC20 token you want to be paid with.
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


        """ From Uniswap contract API

            tokenToTokenSwapInput(
                tokens_sold: uint256,           -> Amount of input ERC20 tokens sold
                min_tokens_bought: uint256,     -> Minimum output ERC20 tokens bought
                min_eth_bought: uint256,        -> Minimum ETH bought as intermediary
                deadline: uint256,              -> Transaction deadline
                token_addr: address             -> Address of output ERC20 token
            ): uint256                          -> Amount of output ERC20 tokens bought



        """

        return Transact(self, self.uniswap_base.web3, self.uniswap_base.abi, self.uniswap_base.exchange, self.uniswap_base._contract,
                        'tokenToTokenSwapInput', [pay_amount.value, buy_amount.value, 1, self.uniswap_base._deadline(), buy_token.address])


    def get_eth_token_output_price(self, amount: Wad):
        return self.uniswap_base.get_eth_token_output_price(amount)

    def get_token_eth_output_price(self, amount: Wad):
        return self.uniswap_base.get_token_eth_output_price(amount)
