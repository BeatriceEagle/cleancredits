.PHONY: lint
lint:
	status=0;\
black . --check || status=1;\
isort --profile black . --check || status=1;\
exit $$status

.PHONY: fmt
fmt:
	black .
	isort --profile black .