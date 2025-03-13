import { NextRequest, NextResponse } from 'next/server'
import { CowService } from '@/app/lib/CowService'
import { OPERATION } from '@/app/lib/constants'

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json()
    const { amount, tokenAddress, operation } = body

    if (!amount || !tokenAddress || !operation) {
      return NextResponse.json(
        { error: 'Amount, tokenAddress, and operation (buy/sell) are required' },
        { status: 400 }
      )
    }

    if (operation !== OPERATION.BUY && operation !== OPERATION.SELL) {
      return NextResponse.json(
        { error: 'Operation must be either buy or sell' },
        { status: 400 }
      )
    }

    const service = await CowService.getInstance()
    const orderId = await service.createSwapOrder({
      amount: BigInt(amount),
      tokenAddress,
      operation
    })
    
    return NextResponse.json({ orderId })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 