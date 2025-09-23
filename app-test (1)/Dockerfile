# Stage 1: Build the React application
FROM node:18-alpine as builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve the React application with Nginx
FROM nginx:alpine

# Remove default Nginx configuration (this is good, as it prevents conflicts)
RUN rm /etc/nginx/conf.d/default.conf

# Copy your custom Nginx configuration (which now only contains the server block)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built React app from the builder stage to Nginx's html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 8080 as required by Cloud Run
EXPOSE 8080

# Command to run Nginx
CMD ["nginx", "-g", "daemon off;"]