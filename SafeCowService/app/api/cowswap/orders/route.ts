import { NextResponse } from 'next/server'
import { OrderBookApi, SupportedChainId } from '@cowprotocol/cow-sdk'
import { CONFIG } from '@/app/lib/config'

export async function GET() {
  try {
    const orderBookApi = new OrderBookApi({ chainId: CONFIG.chainId as SupportedChainId })

    // Get all orders for the Safe address
    const orders = await orderBookApi.getOrders({
      owner: CONFIG.safeAddress,
      limit: 50, // Adjust as needed
      offset: 0
    })

    // Get trades for each order
    const ordersWithTrades = await Promise.all(
      orders.map(async (order) => {
        const trades = await orderBookApi.getTrades({ orderUid: order.uid })
        return {
          order: {
            uid: order.uid,
            status: order.status,
            creationDate: order.creationDate,
            sellToken: order.sellToken,
            buyToken: order.buyToken,
            sellAmount: order.sellAmount,
            buyAmount: order.buyAmount,
            validTo: order.validTo,
            partiallyFillable: order.partiallyFillable,
            executedSellAmount: order.executedSellAmount,
            executedBuyAmount: order.executedBuyAmount,
            invalidated: order.invalidated,
            receiver: order.receiver
          },
          trades: trades.map(trade => ({
            blockNumber: trade.blockNumber,
            logIndex: trade.logIndex,
            orderUid: trade.orderUid,
            sellAmount: trade.sellAmount,
            buyAmount: trade.buyAmount,
            sellToken: trade.sellToken,
            buyToken: trade.buyToken,
          }))
        }
      })
    )

    return NextResponse.json({
      orders: ordersWithTrades
    })
  } catch (error) {
    console.error('Failed to fetch swaps:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 