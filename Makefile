build:
	python3 -m build --sdist --wheel
	twine check dist/*

upload:
	twine upload dist/*

.PHONY: build upload