FROM python:3.9-slim

WORKDIR /app

# Copy project files
COPY . .

# Install the package
RUN pip install --no-cache-dir .

# Use a non-root user for security
RUN useradd -m anymcp
USER anymcp

# Set the entrypoint to the anymcp CLI
ENTRYPOINT ["anymcp"]

# Default command (can be overridden)
CMD ["--help"]
