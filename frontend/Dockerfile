# Use an official Node.js runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (if available)
# Copying them separately takes advantage of Docker's layer caching
COPY package.json ./

# Install dependencies
# If package-lock.json is available, it will be used for a deterministic install
RUN npm install

# Copy the rest of the application's code
COPY . .

# Make port 3000 available to the world outside this container
EXPOSE 3000

# Command to run the app
CMD ["npm", "start"]
