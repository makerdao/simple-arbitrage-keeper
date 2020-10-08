# simple-arbitrage-keeper

This keeper performs simple arbitrage between OasisDex and Uniswap. It's structure is inspired by the original [arbitrage-keeper](www.github.com/makerdao/arbitrage-keeper), which performs arbitrage on the smart contracts powering [Oasis.app](http://oasis.app), `join`, `exit`, `boom` and `bust` in Single Collateral Dai.

This keeper constantly looks for profitable arbitrage opportunities within a token pair across OasisDex and Uniswap and attempts to execute them the moment they becomes available.

It is simple in construction, utilizing the Oasis [REST Api](https://developer.makerdao.com/oasis/api/2/) and on-chain matching engine. It is also bounded by a single token pair and would increase its opportunity horizon and profitability if it evaluates all token pairs, overlapping across both exchanges.

The `opportunity` is defined as the profit amount of the best arbitrage opportunity, which follows a simple call structure:

- Sell `entry_token` and buy `arb_token` on `start_exchange`
- Sell `arb_token` and buy `entry_token` on `end_exchange`

Provided that a `TxManager` is deployed and owned by the `ETH_FROM` address, this keeper can execute contract calls atomically, meaning any failed function call will revert the entire transaction; this prevents the case where `ETH_FROM`, the account the keeper operates from, would be left with the `arb_token` if the selling function call on `end_exchange` fails.

Deployment steps and source code of the `TxManager` can be found here: [https://github.com/makerdao/tx-manager](https://github.com/makerdao/tx-manager).

**We reccommend that first time users go through the [Simple Arbitrage Keeper guide](https://github.com/makerdao/developerguides/blob/master/keepers/simple-arbitrage-keeper/simple-arbitrage-keeper.md).**

## Installation

This project uses *Python 3.6.2*.

In order to clone the project and install required third-party packages please execute:
```
git clone https://github.com/makerdao/simple-arbitrage-keeper.git
cd simple-arbitrage-keeper
git submodule update --init --recursive
pip3 install -r requirements.txt
```

For some known Ubuntu and macOS issues see the [pymaker](https://github.com/makerdao/pymaker) README.

## Usage

While in the `simple-arbitrage-keeper` directory, run the following command with required arguments:
```
usage: simple-arbitrage-keeper [-h] [--rpc-host RPC_HOST]
                               [--rpc-port RPC_PORT]
                               [--rpc-timeout RPC_TIMEOUT] --eth-from ETH_FROM
                               --eth-key [ETH_KEY [ETH_KEY ...]]
                               --uniswap-entry-exchange UNISWAP_ENTRY_EXCHANGE
                               --uniswap-arb-exchange UNISWAP_ARB_EXCHANGE
                               --oasis-address OASIS_ADDRESS
                               --oasis-api-endpoint OASIS_API_ENDPOINT
                               [--relayer-per-page RELAYER_PER_PAGE]
                               --tx-manager TX_MANAGER [--gas-price GAS_PRICE]
                               --entry-token ENTRY_TOKEN --arb-token ARB_TOKEN
                               --arb-token-name ARB_TOKEN_NAME --min-profit
                               MIN_PROFIT --max-engagement MAX_ENGAGEMENT
                               [--max-errors MAX_ERRORS] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --rpc-host RPC_HOST   JSON-RPC host (default: `localhost')
  --rpc-port RPC_PORT   JSON-RPC port (default: `8545')
  --rpc-timeout RPC_TIMEOUT
                        JSON-RPC timeout (in seconds, default: 10)
  --eth-from ETH_FROM   Ethereum address from which to send transactions;
                        checksummed (e.g. '0x12AebC')
  --eth-key [ETH_KEY [ETH_KEY ...]]
                        Ethereum private key(s) to use (e.g. 'key_file=/path/t
                        o/keystore.json,pass_file=/path/to/passphrase.txt')
  --uniswap-entry-exchange UNISWAP_ENTRY_EXCHANGE
                        Ethereum address of the Uniswap Exchange contract for
                        the entry token market; checksummed (e.g. '0x12AebC')
  --uniswap-arb-exchange UNISWAP_ARB_EXCHANGE
                        Ethereum address of the Uniswap Exchange contract for
                        the arb token market; checksummed (e.g. '0x12AebC')
  --oasis-address OASIS_ADDRESS
                        Ethereum address of the OasisDEX contract; checksummed
                        (e.g. '0x12AebC')
  --oasis-api-endpoint OASIS_API_ENDPOINT
                        Endpoint of of the Oasis V2 REST API (e.g. 'https://kovan-api.oasisdex.com' )
  --relayer-per-page RELAYER_PER_PAGE
                        Number of orders to fetch per one page from the 0x
                        Relayer API (default: 100)
  --tx-manager TX_MANAGER
                        Ethereum address of the TxManager contract to use for
                        multi-step arbitrage; checksummed (e.g. '0x12AebC')
  --gas-price GAS_PRICE
                        Gas price in Wei (default: node default), (e.g.
                        1000000000 for 1 GWei)
  --entry-token ENTRY_TOKEN
                        The token address that the bot starts and ends with in
                        every transaction; checksummed (e.g. '0x12AebC')
  --arb-token ARB_TOKEN
                        The token address that arbitraged between both
                        exchanges; checksummed (e.g. '0x12AebC')
  --arb-token-name ARB_TOKEN_NAME
                        The token name that arbitraged between both exchanges
                        (e.g. 'SAI', 'WETH', 'REP')
  --min-profit MIN_PROFIT
                        Ether amount of minimum profit (in base token) from
                        one arbitrage operation (e.g. 1 for 1 Sai min profit)
  --max-engagement MAX_ENGAGEMENT
                        Ether amount of maximum engagement (in base token) in
                        one arbitrage operation (e.g. 100 for 100 Sai max
                        engagement)
  --max-errors MAX_ERRORS
                        Maximum number of allowed errors before the keeper
                        terminates (default: 100)
  --debug               Enable debug output

```

## License

See [COPYING](https://github.com/makerdao/simple-arbitrage-keeper/blob/master/COPYING) file.

## Installation

This project uses *Python 3.6.2*.

In order to clone the project and install required third-party packages please execute:
```
git clone https://github.com/makerdao/arbitrage-keeper.git
cd arbitrage-keeper
git submodule update --init --recursive
pip3 install -r lib/pymaker/requirements.txt
```

For some known Ubuntu and macOS issues see the [pymaker](https://github.com/makerdao/pymaker) README.


### Disclaimer

YOU (MEANING ANY INDIVIDUAL OR ENTITY ACCESSING, USING OR BOTH THE SOFTWARE INCLUDED IN THIS GITHUB REPOSITORY) EXPRESSLY UNDERSTAND AND AGREE THAT YOUR USE OF THE SOFTWARE IS AT YOUR SOLE RISK.
THE SOFTWARE IN THIS GITHUB REPOSITORY IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
YOU RELEASE AUTHORS OR COPYRIGHT HOLDERS FROM ALL LIABILITY FOR YOU HAVING ACQUIRED OR NOT ACQUIRED CONTENT IN THIS GITHUB REPOSITORY. THE AUTHORS OR COPYRIGHT HOLDERS MAKE NO REPRESENTATIONS CONCERNING ANY CONTENT CONTAINED IN OR ACCESSED THROUGH THE SERVICE, AND THE AUTHORS OR COPYRIGHT HOLDERS WILL NOT BE RESPONSIBLE OR LIABLE FOR THE ACCURACY, COPYRIGHT COMPLIANCE, LEGALITY OR DECENCY OF MATERIAL CONTAINED IN OR ACCESSED THROUGH THIS GITHUB REPOSITORY.
