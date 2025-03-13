import { NextRequest, NextResponse } from 'next/server'
import { SafeService } from '@/app/lib/SafeService'

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json()
    const { to, value, data } = body

    if (!to || value === undefined || !data) {
      return NextResponse.json(
        { error: 'to, value, and data are required' },
        { status: 400 }
      )
    }

    const service = SafeService.getInstance()
    await service.initializeSafe()
    
    const { safeTxHash, safeTx, agentSignature } = await service.signTransaction({
      to,
      value,
      data
    })

    return NextResponse.json({ 
      safeTxHash,
      safeTx: {
        to: safeTx.data.to,
        value: safeTx.data.value,
        data: safeTx.data.data,
        operation: safeTx.data.operation
      },
      signature: agentSignature.data
    })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 