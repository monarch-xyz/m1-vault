# API URLs
MORPHO_API_URL = "https://blue-api.morpho.org/graphql"

# Contract Addresses
MORPHO_BLUE_ADDRESS = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
VAULT_ADDRESS = "0x346aac1e83239db6a6cb760e95e13258ad3d1a6d"
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base

# GraphQL Queries
MARKET_APY_QUERY = """
query getMarketAPY($uniqueKey: String!) {
  markets(where:  {
     uniqueKey_in: [$uniqueKey]
  }) {
    items {
      state {
        supplyApy
        borrowApy
        
      }
    }
  }
}
"""

GET_MARKETS_QUERY = """
query getMarkets($first: Int, $where: MarketFilters) {
    markets(first: $first, where: $where) {
        items {
            id
            lltv
            uniqueKey
            oracleAddress
            irmAddress
            loanAsset {
                address
                symbol
                decimals
            }
            collateralAsset {
                address
                symbol
                decimals
            }
            state {
                borrowAssets
                supplyAssets
                borrowAssetsUsd
                supplyAssetsUsd
                utilization
                supplyApy
                borrowApy
            }
        }
    }
}
"""

GET_VAULT_QUERY = """
query getVault($vaultId: String!) {
    vaultByAddress(address: $vaultId, chainId: 8453) {
        state {
            allTimeApy
            apy
            totalAssets
            totalAssetsUsd
            allocation {
                market {
                    id
                    uniqueKey
                    irmAddress
                    oracleAddress
                }
                supplyAssets
                supplyCap
            }
        }
        asset {
            id
            decimals
        }
    }
}
""" 