install:
	poetry install

project:
	poetry run project

build:
	poetry build

publish:
	poetry publish --dry-run

package-install:
	python3 -m pip install dist/*.whl

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

format-check:
	poetry run ruff format --check .

check: lint format-check
	@echo "Все проверки пройдены успешно!"

check-syntax:
	find valutatrade_hub -name "*.py" -exec poetry run python -m py_compile {} \;
	@echo "Синтаксис Python корректен!"
