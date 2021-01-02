ARCH ?= amd64
OS ?= $(shell uname -s | tr '[:upper:]' '[:lower:'])
CURL ?= curl --fail -sSL
XARGS ?= xargs -I {}
BIN_DIR ?= ${HOME}/bin
TMP ?= /tmp
FIND_EXCLUDES ?= -not \( -name .terraform -prune \) -not \( -name .terragrunt-cache -prune \)

PATH := $(BIN_DIR):${PATH}

MAKEFLAGS += --no-print-directory
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: guard/% %/install %/lint

GITHUB_ACCESS_TOKEN ?= 1208df673f14fe3160ce9aaef3600da5480bda9e
# Macro to return the download url for a github release
# For latest release, use version=latest
# To pin a release, use version=tags/<tag>
# $(call parse_github_download_url,owner,repo,version,asset select query)
parse_github_download_url = $(CURL) https://api.github.com/repos/$(1)/$(2)/releases/$(3)?access_token=$(GITHUB_ACCESS_TOKEN) | jq --raw-output  '.assets[] | select($(4)) | .browser_download_url'

# Macro to download a github binary release
# $(call download_github_release,file,owner,repo,version,asset select query)
download_github_release = $(CURL) -o $(1) $(shell $(call parse_github_download_url,$(2),$(3),$(4),$(5)))

# Macro to download a hashicorp archive release
# $(call download_hashicorp_release,file,app,version)
download_hashicorp_release = $(CURL) -o $(1) https://releases.hashicorp.com/$(2)/$(3)/$(2)_$(3)_$(OS)_$(ARCH).zip

guard/env/%:
	@ _="$(or $($*),$(error Make/environment variable '$*' not present))"

guard/program/%:
	@ which $* > /dev/null || $(MAKE) $*/install

$(BIN_DIR):
	@ echo "[make]: Creating directory '$@'..."
	mkdir -p $@

install/gh-release/%: guard/env/FILENAME guard/env/OWNER guard/env/REPO guard/env/VERSION guard/env/QUERY
install/gh-release/%:
	@ echo "[$@]: Installing $*..."
	$(call download_github_release,$(FILENAME),$(OWNER),$(REPO),$(VERSION),$(QUERY))
	chmod +x $(FILENAME)
	$* --version
	@ echo "[$@]: Completed successfully!"

install/pip/%: PYTHON ?= python
install/pip/%: | guard/env/PYPI_PKG_NAME
	@ echo "[$@]: Installing $*..."
	$(PYTHON) -m pip install --user $(PYPI_PKG_NAME)
	ln -sf ~/.local/bin/$* $(BIN_DIR)/$*
	$* --version
	@ echo "[$@]: Completed successfully!"

black/install:
	@ $(MAKE) install/pip/$(@D) PYPI_PKG_NAME=$(@D)

zip/install:
	@ echo "[$@]: Installing $(@D)..."
	apt-get install zip -y
	@ echo "[$@]: Completed successfully!"

terraform/install: TERRAFORM_VERSION_LATEST := $(CURL) https://checkpoint-api.hashicorp.com/v1/check/terraform | jq -r -M '.current_version' | sed 's/^v//'
terraform/install: TERRAFORM_VERSION ?= $(shell $(TERRAFORM_VERSION_LATEST))
terraform/install: | $(BIN_DIR) guard/program/jq
	@ echo "[$@]: Installing $(@D)..."
	$(call download_hashicorp_release,$(@D).zip,$(@D),$(TERRAFORM_VERSION))
	unzip $(@D).zip && rm -f $(@D).zip && chmod +x $(@D)
	mv $(@D) "$(BIN_DIR)"
	$(@D) --version
	@ echo "[$@]: Completed successfully!"

terraform-docs/install: TFDOCS_VERSION ?= latest
terraform-docs/install: | $(BIN_DIR) guard/program/jq
	@ $(MAKE) install/gh-release/$(@D) FILENAME="$(BIN_DIR)/$(@D)" OWNER=segmentio REPO=$(@D) VERSION=$(TFDOCS_VERSION) QUERY='.name | endswith("$(OS)-$(ARCH)")'

jq/install: JQ_VERSION ?= latest
jq/install: | $(BIN_DIR)
	@ $(MAKE) install/gh-release/$(@D) FILENAME="$(BIN_DIR)/$(@D)" OWNER=stedolan REPO=$(@D) VERSION=$(JQ_VERSION) QUERY='.name | endswith("$(OS)64")'

shellcheck/install: SHELLCHECK_VERSION ?= latest
shellcheck/install: SHELLCHECK_URL ?= https://storage.googleapis.com/shellcheck/shellcheck-${SHELLCHECK_VERSION}.linux.x86_64.tar.xz
shellcheck/install: $(BIN_DIR) guard/program/xz
	$(CURL) $(SHELLCHECK_URL) | tar -xJv
	mv $(@D)-*/$(@D) $(BIN_DIR)
	rm -rf $(@D)-*
	$(@D) --version

terraform/lint: | guard/program/terraform
	@ echo "[$@]: Linting Terraform files..."
	terraform fmt -check=true -diff=true
	@ echo "[$@]: Terraform files PASSED lint test!"

terraform/format: | guard/program/terraform
	@ echo "[$@]: Formatting Terraform files..."
	terraform fmt -recursive
	@ echo "[$@]: Successfully formatted terraform files!"

hcl/%: FIND_HCL := find . $(FIND_EXCLUDES) -type f \( -name "*.hcl" \)

## Validates hcl files
hcl/validate: | guard/program/terraform
	@ echo "[$@]: Validating hcl files..."
	@ $(FIND_HCL) | $(XARGS) bash -c 'cat {} | terraform fmt - > /dev/null 2>&1 || (echo "[$@]: Found invalid HCL file: "{}""; exit 1)'
	@ echo "[$@]: hcl files PASSED validation test!"

## Lints hcl files
hcl/lint: | guard/program/terraform hcl/validate
	@ echo "[$@]: Linting hcl files..."
	@ $(FIND_HCL) | $(XARGS) bash -c 'cat {} | terraform fmt -check=true -diff=true - || (echo "[$@]: Found unformatted HCL file: "{}""; exit 1)'
	@ echo "[$@]: hcl files PASSED lint test!"

## Formats hcl files
hcl/format: | guard/program/terraform hcl/validate
	@ echo "[$@]: Formatting hcl files..."
	$(FIND_HCL) | $(XARGS) bash -c 'echo "$$(cat "{}" | terraform fmt -)" > "{}"'
	@ echo "[$@]: Successfully formatted hcl files!"

sh/%: FIND_SH := find . $(FIND_EXCLUDES) -name '*.sh' -type f -print0
sh/lint: | guard/program/shellcheck
	@ echo "[$@]: Linting shell scripts..."
	$(FIND_SH) | $(XARGS) shellcheck {}
	@ echo "[$@]: Shell scripts PASSED lint test!"

json/%: FIND_JSON := find . $(FIND_EXCLUDES) -name '*.json' -type f
json/lint: | guard/program/jq
	@ echo "[$@]: Linting JSON files..."
	$(FIND_JSON) | $(XARGS) bash -c 'cmp {} <(jq --indent 4 -S . {}) || (echo "[{}]: Failed JSON Lint Test"; exit 1)'
	@ echo "[$@]: JSON files PASSED lint test!"

json/format: | guard/program/jq
	@ echo "[$@]: Formatting JSON files..."
	$(FIND_JSON) | $(XARGS) bash -c 'echo "$$(jq --indent 4 -S . "{}")" > "{}"'
	@ echo "[$@]: Successfully formatted JSON files!"

## Runs eclint against the project
eclint/lint: | guard/program/eclint guard/program/git
eclint/lint: HAS_UNTRACKED_CHANGES ?= $(shell cd $(PROJECT_ROOT) && git status -s)
eclint/lint: ECLINT_FILES ?= git ls-files -z
eclint/lint:
	@ echo "[$@]: Running eclint..."
	cd $(PROJECT_ROOT) && \
	[ -z "$(HAS_UNTRACKED_CHANGES)" ] || (echo "untracked changes detected!" && exit 1)
	cd $(PROJECT_ROOT) && \
	$(ECLINT_FILES) | grep -zv ".bats" | xargs -0 -I {} eclint check {}
	@ echo "[$@]: Project PASSED eclint test!"

docs/%: TFDOCS ?= terraform-docs --sort-by-required markdown table
docs/%: README_FILES ?= find . $(FIND_EXCLUDES) -type f -name README.md
docs/%: README_TMP ?= $(TMP)/README.tmp
docs/%: TFDOCS_START_MARKER ?= <!-- BEGIN TFDOCS -->
docs/%: TFDOCS_END_MARKER ?= <!-- END TFDOCS -->

docs/tmp/%: | guard/program/terraform-docs
	@ sed '/$(TFDOCS_START_MARKER)/,/$(TFDOCS_END_MARKER)/{//!d}' $* | awk '{print $$0} /$(TFDOCS_START_MARKER)/ {system("$(TFDOCS) $$(dirname $*)")} /$(TFDOCS_END_MARKER)/ {f=1}' > $(README_TMP)

docs/generate/%:
	@ echo "[$@]: Creating documentation files.."
	@ $(MAKE) docs/tmp/$*
	mv -f $(README_TMP) $*
	@ echo "[$@]: Documentation files creation complete!"

docs/lint/%:
	@ echo "[$@]: Linting documentation files.."
	@ $(MAKE) docs/tmp/$*
	diff $* $(README_TMP)
	rm -f $(README_TMP)
	@ echo "[$@]: Documentation files PASSED lint test!"

## Generates Terraform documentation
docs/generate: | terraform/format
	@ $(README_FILES) | $(XARGS) $(MAKE) docs/generate/{}

## Lints Terraform documentation
docs/lint: | terraform/lint
	@ $(README_FILES) | $(XARGS) $(MAKE) docs/lint/{}

python/lint: | guard/program/black
	@ echo "[$@]: Linting Python files..."
	black --check .
	@ echo "[$@]: Python files PASSED lint test!"

python/format: | guard/program/black
	@ echo "[$@]: Formatting Python files..."
	black .
	@ echo "[$@]: Successfully formatted Python files!"

terratest/install: | guard/program/go
	cd tests && go mod init aws-lambda-ses-forwarder/tests
	cd tests && go build ./...
	cd tests && go mod tidy

terratest/test: | guard/program/go
	cd tests && go test -count=1 -timeout 20m

test: terratest/test

lint: terraform/lint sh/lint json/lint docs/lint python/lint eclint/lint hcl/lint
