LANGUAGES := en zh_CN zh_TW fr_FR ja_JP ko_KR de_DE es_ES

POT_FILE := locale/beanbot.pot
PO_FILES := $(foreach lang,$(LANGUAGES),locale/$(lang)/LC_MESSAGES/beanbot.po)
MO_FILES := $(foreach lang,$(LANGUAGES),locale/$(lang)/LC_MESSAGES/beanbot.mo)

.PHONY: all gentranslations compiletranslations clean

all: gentranslations compiletranslations

gentranslations: $(PO_FILES)

compiletranslations: $(MO_FILES)

$(POT_FILE): **/*.py
	xgettext -d beanbot -o $@ $^

define po_rule
locale/$(1)/LC_MESSAGES/beanbot.po: $(POT_FILE)
	@mkdir -p $$(dir $$@)
	@if [ ! -f $$@ ]; then \
		msginit -i $$< -o $$@ -l $(1); \
	elif [ $$< -nt $$@ ]; then \
		msgmerge --update $$@ $$<; \
	else \
		echo "$$@ is up to date"; \
	fi
endef

$(foreach lang,$(LANGUAGES),$(eval $(call po_rule,$(lang))))

%.mo: %.po
	msgfmt -o $@ $^

# clean:
# 	rm -f $(POT_FILE) $(PO_FILES) $(MO_FILES)
