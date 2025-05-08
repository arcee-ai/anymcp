.PHONY: quality style clean install docker-buildx docker-buildx-push pip pip-upload

# Check that source code meets quality standards
quality:
	black --check --line-length 119 --target-version py38 anymcp
	isort --check-only anymcp
	flake8 --max-line-length 119 anymcp

# Format source code automatically
style:
	black --line-length 119 --target-version py38 anymcp
	isort anymcp

test:
	pytest -sv ./tests/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Install the package
install:
	pip install .

# Install in development mode with test dependencies
dev-install:
	pip install -e ".[dev]"

# Build and package for PyPI
pip:
	rm -rf build/
	rm -rf dist/
	make style && make quality
	python -m build

# Upload to PyPI (adjust repository as needed)
pip-upload:
	twine upload dist/* --verbose --repository anymcp


# Build Docker container for multiple architectures (amd64/x86_64)
docker-buildx:
	docker buildx create --name anymcp-builder --use || true
	docker buildx build --platform linux/amd64 --load -t arceeai/anymcp:latest .

# Build and push Docker container for multiple architectures (amd64/x86_64)
docker-buildx-push:
	docker buildx create --name anymcp-builder --use || true
	docker buildx build --platform linux/amd64 --push -t arceeai/anymcp:latest .