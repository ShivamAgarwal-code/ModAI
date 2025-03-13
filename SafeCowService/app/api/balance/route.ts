import { NextResponse } from 'next/server'
import { CowSwapService } from '@/app/lib/CowSwapService'
import { CONFIG } from '@/app/lib/config'

export const GET = async () => {
  try {
    const service = CowSwapService.getInstance()
    await service.initializeSafe()
    
    const balance = await service.getBalance()
    
    return NextResponse.json({ 
      balance: balance.toString(),
      token: CONFIG.wethAddress 
    })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
} 