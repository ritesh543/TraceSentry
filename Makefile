.PHONY: test check deploy-studionet verify

test:
	python3 -m pytest -v tests/

check:
	bash scripts/run_checks.sh

verify:
	python3 scripts/verify_bundle.py

deploy-studionet:
	bash scripts/deploy_studionet.sh
