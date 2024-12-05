FROM node:20-alpine

WORKDIR /app

# Add build argument
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY package*.json ./
COPY yarn.lock ./

# Configure yarn with longer timeouts and retries
RUN yarn config set network-timeout 600000 && \
    yarn config set registry https://registry.yarnpkg.com && \
    yarn config set httpRetry 5 && \
    yarn config set httpRetryStatusCodes '["429", "500", "502", "503", "504"]'

# Install dependencies with offline mirror and install peer dependencies
RUN yarn install --network-timeout 600000 --prefer-offline --frozen-lockfile && \
    yarn add -D @babel/core tailwindcss@latest

# Copy the rest of the application
COPY . .

# Build the application
RUN yarn build

# Expose port 3000
EXPOSE 3000

# Start the application in production mode
CMD ["yarn", "start"] 