FROM node:20-alpine

WORKDIR /app

# Copy package files for dependency installation
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application source
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

ENV NODE_ENV=production

# Command to run the application
CMD ["npm", "start"]