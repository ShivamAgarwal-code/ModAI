import { NextRequest, NextResponse } from 'next/server'
import { createSafeClient } from '@safe-global/sdk-starter-kit'
import { CONFIG } from '@/app/lib/config'

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json()
    const { signer, safeAddress, safeTxHash } = body

    if (!signer || !safeAddress || !safeTxHash) {
      return NextResponse.json(
        { error: 'Signer, safeAddress, and safeTxHash are required' },
        { status: 400 }
      )
    }

    const safeClient = await createSafeClient({
      provider: CONFIG.rpcUrl,
      signer,
      safeAddress
    })

    const pendingTransactions = await safeClient.getPendingTransactions()
    let isConfirmed = false

    for (const transaction of pendingTransactions.results) {
      if (transaction.safeTxHash !== safeTxHash) {
        continue
      }

      const txResult = await safeClient.confirm({ safeTxHash })
      isConfirmed = true
      return NextResponse.json({ txResult })
    }

    if (!isConfirmed) {
      return NextResponse.json(
        { error: 'Transaction not found in pending transactions' },
        { status: 404 }
      )
    }

  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 