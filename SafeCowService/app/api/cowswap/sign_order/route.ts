import { NextRequest, NextResponse } from 'next/server'
import { CowService } from '@/app/lib/CowService'

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json()
    const { orderId } = body

    if (!orderId) {
      return NextResponse.json(
        { error: 'Order ID is required' },
        { status: 400 }
      )
    }

    const service = await CowService.getInstance()
    const { safeTxHash, safeTx } = await service.agentSignTransaction(orderId)

    return NextResponse.json({ 
      safeTxHash,
      safeTx: {
        to: safeTx.data.to,
        value: safeTx.data.value,
        data: safeTx.data.data,
        operation: safeTx.data.operation
      }
    })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 