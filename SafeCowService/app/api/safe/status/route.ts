import { NextRequest, NextResponse } from 'next/server'
import { createSafeClient } from '@safe-global/sdk-starter-kit'
import { CONFIG } from '@/app/lib/config'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const safeTxHash = searchParams.get('safeTxHash')

    if (!safeTxHash) {
      return NextResponse.json(
        { error: 'safeTxHash query parameter is required' },
        { status: 400 }
      )
    }

    const safeClient = await createSafeClient({
      provider: CONFIG.rpcUrl,
      signer: CONFIG.agentPrivateKey,
      safeAddress: CONFIG.safeAddress
    })

    const pendingTxs = await safeClient.getPendingTransactions()
    const tx = pendingTxs.results.find(tx => tx.safeTxHash === safeTxHash)

    if (!tx) {
      return NextResponse.json({
        status: 'unknown',
        message: 'Transaction not found in pending queue'
      })
    }

    const threshold = await safeClient.getThreshold()
    const confirmations = tx.confirmations?.length || 0

    return NextResponse.json({
      status: 'pending',
      transaction: {
        safeTxHash: tx.safeTxHash,
        confirmations,
        threshold,
        isExecutable: confirmations >= threshold,
      }
    })
  } catch (error) {
    console.error('Safe status check error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 