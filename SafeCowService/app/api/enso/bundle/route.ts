import { NextRequest, NextResponse } from 'next/server'
import { CONFIG } from '@/app/lib/config'
import { SafeService } from '@/app/lib/SafeService'

const ENSO_API_URL = 'https://api.enso.finance/api/v1/shortcuts/bundle'

type BundleAction = {
  protocol: string
  action: string
  args: Record<string, any>
}

export async function POST(request: NextRequest) {
  try {
    const actions: BundleAction[] = await request.json()

    if (!Array.isArray(actions) || actions.length === 0) {
      return NextResponse.json(
        { error: 'Request body must be a non-empty array of actions' },
        { status: 400 }
      )
    }

    // Build Enso API request URL
    const ensoParams = new URLSearchParams({
      chainId: CONFIG.chainId.toString(),
      fromAddress: CONFIG.safeAddress,
      receiver: CONFIG.safeAddress,
      spender: CONFIG.safeAddress,
      routingStrategy: 'delegate'
    })

    const response = await fetch(`${ENSO_API_URL}?${ensoParams}`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(actions)
    })

    if (!response.ok) {
      throw new Error(`Enso API error: ${response.statusText}`)
    }

    const data = await response.json()

    // Sign the bundle transaction with Safe
    const safeService = SafeService.getInstance()
    await safeService.initializeSafe()

    const { safeTxHash, safeTx } = await safeService.signTransaction({
      to: data.tx.to,
      value: data.tx.value,
      data: data.tx.data
    })

    return NextResponse.json({
      route: data.route,
      gas: data.gas,
      safeTxHash,
      transaction: {
        to: safeTx.data.to,
        value: safeTx.data.value,
        data: safeTx.data.data,
        operation: safeTx.data.operation
      }
    })
  } catch (error) {
    console.error('Bundle execution error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 