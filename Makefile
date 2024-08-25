LANGUAGES := en zh_CN zh_TW fr_FR ja_JP ko_KR de_DE es_ES

DOMAIN := beanbot
POT_FILE := locale/$(DOMAIN).pot
PO_FILES := $(foreach lang,$(LANGUAGES),locale/$(lang)/LC_MESSAGES/$(DOMAIN).po)
MO_FILES := $(foreach lang,$(LANGUAGES),locale/$(lang)/LC_MESSAGES/$(DOMAIN).mo)

.PHONY: all gentranslations compiletranslations clean lint

all: gentranslations compiletranslations

gentranslations: $(PO_FILES)

compiletranslations: $(MO_FILES)

$(POT_FILE): **/*.py
	xgettext -d $(DOMAIN) -o $@ $^

define po_rule
locale/$(1)/LC_MESSAGES/$(DOMAIN).po: $(POT_FILE)
	@mkdir -p $$(dir $$@)
	@if [ ! -f $$@ ]; then \
		msginit -i $$< -o $$@ -l $(1); \
	else \
		msgmerge --update $$@ $$<; \
	fi
endef

$(foreach lang,$(LANGUAGES),$(eval $(call po_rule,$(lang))))

%.mo: %.po
	msgfmt -o $@ $^

# clean:
# 	rm -f $(POT_FILE) $(PO_FILES) $(MO_FILES)

lint:
	@ruff check

test:
	coverage run -m pytest
	coverage report --include="**/*.py" --omit="**/*_test.py"
	@coverage html --include="**/*.py" --omit="**/*_test.py"
