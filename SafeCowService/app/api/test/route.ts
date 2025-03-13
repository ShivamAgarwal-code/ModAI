import { NextResponse } from 'next/server'
import { TradingSdk, OrderKind, SigningScheme, SupportedChainId } from '@cowprotocol/cow-sdk'
import { VoidSigner } from '@ethersproject/abstract-signer'
import { JsonRpcProvider } from '@ethersproject/providers'
import { CONFIG } from '@/app/lib/config'
import { WETH_ADDRESS, COW_ADDRESS } from '@/app/lib/constants'

export async function GET() {
  try {
    // Initialize SDK
    const cowSdk = new TradingSdk({
      chainId: CONFIG.chainId as SupportedChainId,
      signer: new VoidSigner(
        CONFIG.safeAddress,
        new JsonRpcProvider(CONFIG.simulatorRpcUrl)
      ),
      appCode: CONFIG.appCode
    })

    // Create order parameters
    const parameters = {
      kind: OrderKind.SELL,
      sellToken: WETH_ADDRESS,
      sellTokenDecimals: 18,
      buyToken: COW_ADDRESS,
      buyTokenDecimals: 18,
      amount: '5000000000000000', // 0.01 WETH
      receiver: CONFIG.safeAddress
    }

    const advancedParameters = {
      quoteRequest: {
        signingScheme: SigningScheme.PRESIGN,
      }
    }

    console.log('Posting order with params:', parameters)
    const orderId = await cowSdk.postSwapOrder(parameters, advancedParameters)
    console.log(`Order ID: [${orderId}]`)

    const preSignTransaction = await cowSdk.getPreSignTransaction({
      orderId,
      account: CONFIG.safeAddress,
    })
    console.log('PreSign transaction:', preSignTransaction)

    return NextResponse.json({ 
      success: true,
      orderId,
      preSignTransaction: {
        to: preSignTransaction.to,
        value: preSignTransaction.value,
        data: preSignTransaction.data
      }
    })
  } catch (error) {
    console.error('Test endpoint error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 