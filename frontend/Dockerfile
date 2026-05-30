FROM node:24

WORKDIR /app

# Copy manifests first for better layer caching
COPY package.json package-lock.json* ./

# Install all dependencies (dev + prod)
RUN npm install

# Copy source
COPY . .

# Production build (used when CMD is not overridden)
RUN npm run build

EXPOSE 3000

# Production default: serve the built output on port 3000
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]
