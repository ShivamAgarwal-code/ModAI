import { NextResponse } from 'next/server'
import { CowSwapService } from '@/app/lib/CowSwapService'
import { CONFIG } from '@/app/lib/config'

export const GET = async () => {
  try {
    const service = CowSwapService.getInstance()
    await service.initializeSafe()
    
    // Get native token (ETH) balance from Safe SDK
    const ethBalance = await service.getBalance()
    
    // Get all token balances from Safe Transaction Service
    const response = await fetch(
      `https://safe-transaction-sepolia.safe.global/api/v1/safes/${CONFIG.safeAddress}/balances/`,
      {
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      }
    )

    if (!response.ok) {
      throw new Error('Failed to fetch token balances')
    }

    const tokenBalances = await response.json()
    
    return NextResponse.json({ 
      address: service.getSafeAddress(),
      nativeBalance: ethBalance.toString(),
      tokens: tokenBalances.map((token: any) => ({
        tokenAddress: token.tokenAddress,
        balance: token.balance,
        token: token.token ? {
          name: token.token.name,
          symbol: token.token.symbol,
          decimals: token.token.decimals,
          logoUri: token.token.logoUri
        } : null
      }))
    })
  } catch (error) {
    console.error('Balance fetch error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 