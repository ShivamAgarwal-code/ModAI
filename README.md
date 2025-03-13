## Mod AI


## Services Setup Guide

This repository contains three microservices that work together:
- **AgentZerePy**: Main agent service
- **SafeCowService**: Web interface service
- **TgNotifyService**: Telegram notification service


## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for SafeCowService)
- Python 3.11+ (for AgentZerePy and TgNotifyService)
- pnpm (for SafeCowService)
- Poetry (for Python services)

## Network Setup

All services communicate through a shared Docker network. It will be created automatically when running the services.(BUT MANUALLY SETUP 👇👇👇 )

## Service Configuration

### AgentZerePy

1. Navigate to AgentZerePy directory:
```bash
cd AgentZerePy
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Build and run:
```bash
poetry run python main.py
```

Service will be available at `http://localhost:3000`

### SafeCowService

1. Navigate to SafeCowService directory:
```bash
cd SafeCowService
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Install dependencies and build:
```bash
pnpm install
```

4. Run the service:
```bash
pnpm dev
```

Service will be available at `http://localhost:16000`

### TgNotifyService

1. Navigate to TgNotifyService directory:
```bash
cd TgNotifyService
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Build and run:
```bash
poetry run uvicorn src.main:app --host 0.0.0.0 --port 16000
```

## Development

Each service has its own development workflow:

- **AgentZerePy**: Uses Poetry for dependency management. Run `poetry install` for local development.
- **SafeCowService**: Uses pnpm. Run `pnpm dev` for local development.
- **TgNotifyService**: Uses Poetry. Run `poetry install` for local development.

## Using just

All services support `just` command runner for common tasks:

```bash
# In any service directory
just b  # Build the service
just u   # Start the service
just k   # Stop the service
```

## Environment Variables

Each service requires specific environment variables. Check `.env.example` files in each service directory for required variables.

## Troubleshooting

1. If services can't connect to each other, ensure the `cow-service-network` Docker network exists:
```bash
docker network create cow-service-network
```

2. For Redis connection issues, check if Redis is running and password is correctly set in environment variables.

3. For port conflicts, modify the port mappings in respective `docker-compose.yml` files. 

## Zodiac Roles Setup

1. Navigate to ZodiacRoles directory:
```bash
cd ZodiacRoles
```

2. Install dependencies:
```bash
yarn
```

2. Configure permissions:
   - Copy `.env.example` to `.env` in each service directory and fill in your values
   - Update token configurations in eth-sdk/config.ts for swapper and transfer roles
   - Adjust transfer permissions in src/roles/transfer.ts as needed

3. Generate transactions:
```bash
yarn eth/sdk && yarn start
```

4. Upload to Safe's Wallet through SafeCowService:
    - use SafeCowService:
        - localhost:3000/create_tx - to create a tx
        - localhost:3000/confirm_tx - to confirm a tx
  
4. or upload to Safe's transaction builder (base method):
   - Use the generated JSON file
   - Execute transactions through Safe's multisig process

### Using Permissioned Smart Account

Recommendation: For token operations, you can use [Zodiac Pilot](https://pilot.gnosisguild.org) to route transactions through the Roles mod contract, build batches, and optimize gas usage.
