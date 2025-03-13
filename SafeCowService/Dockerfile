FROM node:20-slim

WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm

# Set pnpm store directory
RUN pnpm config set store-dir /app/.pnpm-store

# Copy package files
COPY package*.json pnpm-lock.yaml ./

# Install all dependencies including devDependencies
RUN pnpm install --frozen-lockfile

# Install required TypeScript dependencies
RUN pnpm add -D typescript @types/node @types/react @types/react-dom

# Copy the rest of the code
COPY . .

# Build the app
RUN pnpm build

EXPOSE 3000

# Start the app
CMD ["pnpm", "start"]