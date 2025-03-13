import { NextRequest, NextResponse } from 'next/server'
import { CONFIG } from '@/app/lib/config'

const ENSO_API_URL = 'https://api.enso.finance/api/v1/shortcuts/quote'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const tokenIn = searchParams.get('tokenIn')
    const tokenOut = searchParams.get('tokenOut')
    const amountIn = searchParams.get('amountIn')

    if (!tokenIn || !tokenOut || !amountIn) {
      return NextResponse.json(
        { error: 'Missing required parameters: tokenIn, tokenOut, or amountIn' },
        { status: 400 }
      )
    }

    // Build Enso API request URL
    const ensoParams = new URLSearchParams({
      chainId: CONFIG.chainId.toString(),
      fromAddress: CONFIG.safeAddress,
      tokenIn,
      tokenOut,
      amountIn,
      priceImpact: 'true'
    })

    const response = await fetch(`${ENSO_API_URL}?${ensoParams}`, {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`Enso API error: ${response.statusText}`)
    }

    const data = await response.json()

    return NextResponse.json({
      gas: data.gas,
      amountOut: data.amountOut,
      priceImpact: data.priceImpact
    })
  } catch (error) {
    console.error('Quote calculation error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 